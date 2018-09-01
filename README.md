# AnkiPy

This is a port of [AnkiSharp](https://github.com/AnkiTools/AnkiSharp) for Python. It allows you to create, read and edit Anki files.

### PyPI

```
pip install AnkiPy
```

### Basic usage

``` python
from AnkiPy import Anki

test_anki = Anki(_PATH_FOR_ANKI_FILE_)
test_deck = test_anki.deck(_DECK_NAME_)

test_deck.add_item("Hello", "Bonjour")
test_deck.add_item("How are you ?", "Comment ca va ?")
test_deck.add_item("Flower", "fleur")
test_deck.add_item("House", "Maison")
```

### Setting fields

``` python
// Permits to set more than two fields. However, by default, only first two fields are used.
// Everything before '<hr id=answer>' is the front of the card, everything after is the behind
// Permits to change the css of your cards (optional). You can just leave this out, it will use the default CSS.
test_note = test_anki.new_note(
    name=_NOTE_NAME_,
    fields=["English", "Spanish", "French"],
    templates=["{0} - {1} \\n<hr id=answer>\\n {2}"],
    css=_CSS_STRING_
)

test_deck.add_item("Hello", "Hola", "Bonjour", note=test_note)
test_deck.add_item("How are you ?", "Como estas?", "Comment ca va ?", note=test_note)
test_deck.add_item("Flower", "flor", "fleur", note=test_note)
test_deck.add_item("House", "Casa", "Maison", note=test_note)
```

### Editing CSS

``` python
// Editing the CSS is also possible.
test_note2 = test_anki.get_note(_ANOTHER_NOTE_NAME_)
assert test_note2 == _CSS_STRING_
test_note2.css = _NEW_CSS_STRING_
```

## TO-DO

:ok_hand: = Done

:zzz: = Waiting for you to be developed

- Add more fields to the cards :ok_hand:
- Possibility to change the card's CSS :ok_hand:
- Being able to show what's on the front and on the back of the card :ok_hand:
- Get the words for other apkg files :ok_hand:
- When added from apkg file, copy cards' metadata (when to review them, ...) :ok_hand:
- Copy the revlog entries :ok_hand:
- Optimize CardMetadata and RevLogMetadata struct (doesn't need to be all doubles) :ok_hand:
- If apkg or temp files already exists remove them :ok_hand:
- ContainsItem with lambda as parameter to compare two objects :ok_hand:
- A deck can have different fields for the cards :ok_hand:
- Conf, decks, dconf, models.mod need to be managable :zzz:
- Hint field :ok_hand:
- Type field :ok_hand:
- Special fields :zzz:
- Media and latex :zzz:
- Conditional tags :zzz:
- Cloze tags :zzz:
- Sub deck support :zzz:
- Synchronize with ankiweb ? :zzz:
- Refactoring :zzz:
- Add images and audio :zzz:
- Generate audio with synthetizer or other tools? :ok_hand:

## Resources

- [Anki APKG format documentation](http://decks.wikia.com/wiki/Anki_APKG_format_documentation)
- [Database Structure](https://github.com/ankidroid/Anki-Android/wiki/Database-Structure)