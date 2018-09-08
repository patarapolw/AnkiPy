import pytest
from pathlib import Path
import shutil
from nonrepeat import nonrepeat_filename

from AnkiPy import Anki


@pytest.mark.parametrize('in_file', [
    'not-existed.apkg',
    'test.apkg'
])
@pytest.mark.parametrize('has_template', [True, False])
@pytest.mark.parametrize('has_css', [True, False])
def test_basic(in_file, has_template, has_css):
    out_file = nonrepeat_filename(str(Path('tests/output').joinpath(in_file)))
    in_path = Path('tests/input').joinpath(in_file)
    if in_path.exists():
        shutil.copy(str(in_path), out_file)

    test_anki = Anki(out_file)
    test_deck = test_anki.deck('test')

    test_deck.add_item("Hello", "Bonjour")
    test_deck.add_item("How are you ?", "Comment ca va ?")
    test_deck.add_item("Flower", "fleur")
    test_deck.add_item("House", "Maison")

    model_kwargs = dict(
        name='test_model',
        fields=["English", "Spanish", "French"]
    )

    if has_template:
        model_kwargs['templates'] = ["{0} - {1} \n<hr id=answer>\n {2}"]
    if has_css:
        model_kwargs['css'] = '.card { font-family: Tahoma; }'

    test_anki.new_model(
        **model_kwargs
    )

    test_deck.add_item("Hello", "Hola", "Bonjour", model='test_model')
    test_deck.add_item("How are you ?", "Como estas?", "Comment ca va ?", model='test_model')
    test_deck.add_item("Flower", "flor", "fleur", model='test_model')
    test_deck.add_item("House", "Casa", "Maison", model='test_model')

    test_anki.close()


@pytest.mark.parametrize('in_file', [
    'not-existed.apkg',
    'test.apkg'
])
@pytest.mark.parametrize('has_template', [True, False])
@pytest.mark.parametrize('has_css', [True, False])
def test_basic_context(in_file, has_template, has_css):
    out_file = nonrepeat_filename(str(Path('tests/output').joinpath(in_file)))
    in_path = Path('tests/input').joinpath(in_file)
    if in_path.exists():
        shutil.copy(str(in_path), out_file)

    with Anki(out_file) as test_anki:
        test_deck = test_anki.deck('test')

        test_deck.add_item("Hello", "Bonjour")
        test_deck.add_item("How are you ?", "Comment ca va ?")
        test_deck.add_item("Flower", "fleur")
        test_deck.add_item("House", "Maison")

        model_kwargs = dict(
            name='test_model',
            fields=["English", "Spanish", "French"]
        )

        if has_template:
            model_kwargs['templates'] = ["{0} - {1} \n<hr id=answer>\n {2}"]
        if has_css:
            model_kwargs['css'] = '.card { font-family: Tahoma; }'

        test_anki.new_model(
            **model_kwargs
        )

        test_deck.add_item("Hello", "Hola", "Bonjour", model='test_model')
        test_deck.add_item("How are you ?", "Como estas?", "Comment ca va ?", model='test_model')
        test_deck.add_item("Flower", "flor", "fleur", model='test_model')
        test_deck.add_item("House", "Casa", "Maison", model='test_model')
