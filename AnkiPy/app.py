import sqlite3
import json
from collections import OrderedDict
from copy import deepcopy
from time import time
from bs4 import BeautifulSoup
from hashlib import sha1
from zipfile import ZipFile
from tempfile import mkdtemp
from pathlib import Path
import shutil
import atexit
import re

from .tools.defaults import DEFAULTS
from .tools.guid import guid64


class AnkiDatabase:
    def __init__(self, conn):
        """

        :param sqlite3.Connection conn:
        """
        self.conn = conn
        self.conn.row_factory = sqlite3.Row

        self.ids = dict()

        self.init()

    def init(self):
        cursor = self.conn.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table" AND name = "col"')
        if cursor.fetchone()[0] != 1:
            self.conn.executescript('''
-- Cards are what you review. 
-- There can be multiple cards for each note, as determined by the Template.
CREATE TABLE cards (
    id              integer primary key,
      -- the epoch milliseconds of when the card was created
    nid             integer not null,--    
      -- notes.id
    did             integer not null,
      -- deck id (available in col table)
    ord             integer not null,
      -- ordinal : identifies which of the card templates it corresponds to 
      --   valid values are from 0 to num templates - 1
    mod             integer not null,
      -- modificaton time as epoch seconds
    usn             integer not null,
      -- update sequence number : used to figure out diffs when syncing. 
      --   value of -1 indicates changes that need to be pushed to server. 
      --   usn < server usn indicates changes that need to be pulled from server.
    type            integer not null,
      -- 0=new, 1=learning, 2=due, 3=filtered
    queue           integer not null,
      -- -3=sched buried, -2=user buried, -1=suspended,
      -- 0=new, 1=learning, 2=due (as for type)
      -- 3=in learning, next rev in at least a day after the previous review
    due             integer not null,
     -- Due is used differently for different card types: 
     --   new: note id or random int
     --   due: integer day, relative to the collection's creation time
     --   learning: integer timestamp
    ivl             integer not null,
      -- interval (used in SRS algorithm). Negative = seconds, positive = days
    factor          integer not null,
      -- factor (used in SRS algorithm)
    reps            integer not null,
      -- number of reviews
    lapses          integer not null,
      -- the number of times the card went from a "was answered correctly" 
      --   to "was answered incorrectly" state
    left            integer not null,
      -- reps left till graduation
    odue            integer not null,
      -- original due: only used when the card is currently in filtered deck
    odid            integer not null,
      -- original did: only used when the card is currently in filtered deck
    flags           integer not null,
      -- currently unused
    data            text not null
      -- currently unused
);

-- col contains a single row that holds various information about the collection
CREATE TABLE col (
    id              integer primary key,
      -- arbitrary number since there is only one row
    crt             integer not null,
      -- created timestamp
    mod             integer not null,
      -- last modified in milliseconds
    scm             integer not null,
      -- schema mod time: time when "schema" was modified. 
      --   If server scm is different from the client scm a full-sync is required
    ver             integer not null,
      -- version
    dty             integer not null,
      -- dirty: unused, set to 0
    usn             integer not null,
      -- update sequence number: used for finding diffs when syncing. 
      --   See usn in cards table for more details.
    ls              integer not null,
      -- "last sync time"
    conf            text not null,
      -- json object containing configuration options that are synced
    models          text not null,
      -- json array of json objects containing the models (aka Note types)
    decks           text not null,
      -- json array of json objects containing the deck
    dconf           text not null,
      -- json array of json objects containing the deck options
    tags            text not null
      -- a cache of tags used in the collection (This list is displayed in the browser. Potentially at other place)
);

-- Contains deleted cards, notes, and decks that need to be synced. 
-- usn should be set to -1, 
-- oid is the original id.
-- type: 0 for a card, 1 for a note and 2 for a deck
CREATE TABLE graves (
    usn             integer not null,
    oid             integer not null,
    type            integer not null
);

-- Notes contain the raw information that is formatted into a number of cards
-- according to the models
CREATE TABLE notes (
    id              integer primary key,
      -- epoch seconds of when the note was created
    guid            text not null,
      -- globally unique id, almost certainly used for syncing
    mid             integer not null,
      -- model id
    mod             integer not null,
      -- modification timestamp, epoch seconds
    usn             integer not null,
      -- update sequence number: for finding diffs when syncing.
      --   See the description in the cards table for more info
    tags            text not null,
      -- space-separated string of tags. 
      --   includes space at the beginning and end, for LIKE "% tag %" queries
    flds            text not null,
      -- the values of the fields in this note. separated by 0x1f (31) character.
    sfld            text not null,
      -- sort field: used for quick sorting and duplicate check
    csum            integer not null,
      -- field checksum used for duplicate check.
      --   integer representation of first 8 digits of sha1 hash of the first field
    flags           integer not null,
      -- unused
    data            text not null
      -- unused
);

-- revlog is a review history; it has a row for every review you've ever done!
CREATE TABLE revlog (
    id              integer primary key,
       -- epoch-milliseconds timestamp of when you did the review
    cid             integer not null,
       -- cards.id
    usn             integer not null,
        -- update sequence number: for finding diffs when syncing. 
        --   See the description in the cards table for more info
    ease            integer not null,
       -- which button you pushed to score your recall. 
       -- review:  1(wrong), 2(hard), 3(ok), 4(easy)
       -- learn/relearn:   1(wrong), 2(ok), 3(easy)
    ivl             integer not null,
       -- interval
    lastIvl         integer not null,
       -- last interval
    factor          integer not null,
      -- factor
    time            integer not null,
       -- how many milliseconds your review took, up to 60000 (60s)
    type            integer not null
       --  0=learn, 1=review, 2=relearn, 3=cram
);


CREATE INDEX ix_cards_nid on cards (nid);
CREATE INDEX ix_cards_sched on cards (did, queue, due);
CREATE INDEX ix_cards_usn on cards (usn);
CREATE INDEX ix_notes_csum on notes (csum);
CREATE INDEX ix_notes_usn on notes (usn);
CREATE INDEX ix_revlog_cid on revlog (cid);
CREATE INDEX ix_revlog_usn on revlog (usn);
            ''')

        self.ids = {
            'did': set(),
            'mid': set(),
            'nid': set(),
            'cid': set(),
            'guid': set()
        }

        cursor = self.conn.execute('SELECT decks, models FROM col')
        for row in cursor:
            self.ids['did'] = set(json.loads(row['decks']).keys())
            self.ids['mid'] = set(json.loads(row['models']).keys())

        cursor = self.conn.execute('SELECT id, guid FROM notes')
        for row in cursor:
            self.ids['nid'].add(row[0])
            self.ids['guid'].add(row[1])

        cursor = self.conn.execute('SELECT id FROM cards')
        for row in cursor:
            self.ids['cid'].add(row[0])

    def deck(self, name, create=None):
        col = deepcopy(DEFAULTS['col'])

        db_col = self.conn.execute('SELECT decks FROM col').fetchone()
        if db_col is None:
            if create is False:
                raise ValueError('{} does not exists.'.format(name))
            else:
                decks = dict()
                # models = dict()
                col.update({
                    'decks': json.dumps(decks),
                    # 'models': json.dumps(models)
                })
                self.conn.execute('INSERT INTO col ({}) VALUES ({})'.format(','.join(col.keys()),
                                                                            ','.join('?' for _ in col.keys())),
                                  tuple(col.values()))
        else:
            decks = json.loads(db_col[0], object_pairs_hook=OrderedDict)

        deck = None
        for v in decks.values():
            if name == v['name']:
                deck = v

        if deck is not None:
            if create is True:
                raise ValueError('{} already exists'.format(name))
            else:
                return AnkiDeck(deck, self)
        else:
            col = deepcopy(DEFAULTS['col'])
            deck_id = self._new_id('did')
            decks[str(deck_id)] = tuple(json.loads(col['decks']).values())[0]
            decks[str(deck_id)].update({
                'id': deck_id,
                'name': name
            })

            self.conn.execute('UPDATE col SET decks=?', (json.dumps(decks), ))
            self.conn.commit()

            return AnkiDeck(decks[str(deck_id)], self)

    def new_deck(self, deck_name):
        return self.deck(deck_name, create=True)

    def get_deck(self, deck_name):
        return self.deck(deck_name, create=False)

    def add_item(self, *args, **kwargs):
        note = deepcopy(DEFAULTS['notes'])
        sfld = BeautifulSoup(args[0], 'html.parser').text
        nid = self._new_id('nid')

        model = self._model(name=kwargs.get('model', 'Basic'))

        note.update({
            'id': nid,
            'guid': self._new_guid(),
            'mid': model['id'],
            'mod': int(time()),
            'tags': kwargs.get('tags', ''),
            'flds': '\x1f'.join(args),
            'sfld': sfld,
            'csum': sha1(sfld.encode('utf8')).hexdigest()
        })

        self.conn.execute('INSERT INTO notes ({}) VALUES ({})'.format(','.join(note.keys()),
                                                                      ','.join('?' for _ in note.keys())),
                          tuple(note.values()))

        card = deepcopy(DEFAULTS['cards'])
        cid = self._new_id('cid')

        for order in range(len(model['tmpls'])):
            deck_names = kwargs.get('decks', None)
            if deck_names is not None:
                deck = self.deck(deck_names[order])
            else:
                deck = self.deck(kwargs.get('deck'))

            card.update({
                'id': cid,
                'nid': nid,
                'did': deck.id,
                'ord': order,
                'mod': int(time())
            })

            self.conn.execute('INSERT INTO cards ({}) VALUES ({})'.format(','.join(card.keys()),
                                                                          ','.join('?' for _ in card.keys())),
                              tuple(card.values()))
        self.conn.commit()

    def _new_id(self, id_type):
        id_value = int(time() * 1000)
        while id_value in self.ids[id_type]:
            id_value += 1
        self.ids[id_type].add(id_value)

        return id_value

    def _new_guid(self):
        guid = guid64()
        while guid in self.ids['guid']:
            guid = guid64()
        self.ids['guid'].add(guid)

        return guid

    def _model(self, name):
        cursor = self.conn.execute('SELECT models FROM col')
        models = json.loads(cursor.fetchone()[0])

        for k, v in models.items():
            if v['name'] == name:
                return v

        raise ValueError('{} not in models'.format(name))

    def new_model(self, name, fields, templates=None, css=None):
        col = deepcopy(DEFAULTS['col'])

        cursor = self.conn.execute('SELECT models FROM col')
        if cursor is None:
            raise ValueError('A deck must be created first.')
        else:
            models = json.loads(cursor.fetchone()[0], object_pairs_hook=OrderedDict)

        if name in models.keys():
            raise ValueError('{} already exists'.format(name))
        else:
            model_id = self._new_id('mid')
            models[str(model_id)] = tuple(json.loads(col['models']).values())[0]
            model = models[str(model_id)]

            flds = []
            for i, field_name in enumerate(fields):
                fld = deepcopy(model['flds'][0])
                fld.update({
                    'name': field_name,
                    'ord': i
                })
                flds.append(fld)

            if templates is None:
                tmpls = self._model('Basic')['tmpls']
            else:
                tmpls = []
                for i, template in enumerate(templates):
                    if isinstance(template, (dict, OrderedDict)):
                        tmpl = template
                    else:
                        tmpl = deepcopy(model['tmpls'][0])

                        if isinstance(template, str):
                            template = template\
                                .format(*('{{%s}}' % field_name for field_name in fields))
                            qfmt, afmt = re.fullmatch(r'(.*)(<hr id=answer>.*)', template, flags=re.DOTALL).groups()
                            afmt = '{{FrontSide}}' + afmt
                        else:
                            qfmt = template[0]
                            afmt = template[1]

                        tmpl.update({
                            'name': 'Card {}'.format(i + 1),
                            'ord': i,
                            'qfmt': qfmt,
                            'afmt': afmt
                        })

                    tmpls.append(tmpl)

            if css is None:
                css = self._model('Basic')['css']

            models[str(model_id)].update({
                'name': name,
                'flds': flds,
                'id': model_id,
                'mod': int(time()),
                'tmpls': tmpls,
                'css': css
            })

            self.conn.execute('UPDATE col SET models=?', (json.dumps(models), ))
            self.conn.commit()

            return models[str(model_id)]


class AnkiDeck:
    def __init__(self, deck, anki):
        """

        :param dict|OrderedDict deck:
        :param AnkiDatabase anki:
        """
        self.name = deck['name']
        self.id = deck['id']
        self.anki = anki

    def add_item(self, *args, **kwargs):
        return self.anki.add_item(deck=self.name, *args, **kwargs)


class Anki(AnkiDatabase):
    def __init__(self, filename):
        self.filename = filename
        self.temp_dir = mkdtemp()
        atexit.register(shutil.rmtree, self.temp_dir, ignore_errors=True)

        if Path(filename).exists():
            with ZipFile(filename) as zf:
                zf.extractall(path=self.temp_dir)

        super().__init__(sqlite3.connect(str(Path(self.temp_dir).joinpath('collection.anki2'))))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def close(self):
        self.save()
        shutil.rmtree(self.temp_dir)

    def save(self):
        with ZipFile(self.filename, 'w') as zf:
            zf.write(str(Path(self.temp_dir).joinpath('collection.anki2')), arcname='collection.anki2')
            zf.writestr('media', '{}')
