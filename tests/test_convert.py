from types import SimpleNamespace as NS

from ocrmypdf.hocrtransform import OcrClass

from ocrmypdf_indra.convert import page_to_tree, split_words, to_input_frame


def line(box, text, conf=0.9):
    return NS(box=box, text=text, conf=conf)


def page(lines, blocks=(), rotation=0):
    return NS(lines=lines, blocks=list(blocks), rotation=rotation)


def test_split_words_is_proportional_and_covers_the_line():
    words = split_words("ab cdef", [0, 10, 70, 30])
    assert [w.text for w in words] == ["ab", "cdef"]
    assert words[0].bbox.left == 0
    assert words[1].bbox.right == 70
    # 2 + 1 + 4 = 7 characters -> 10 px each
    assert (words[0].bbox.right, words[1].bbox.left) == (20, 30)


def test_split_words_rtl_runs_right_to_left():
    words = split_words("ab cd", [0, 0, 50, 10], rtl=True)
    assert words[0].text == "ab" and words[0].bbox.right == 50
    assert words[1].bbox.left == 0


def test_tree_shape_and_text():
    p = page([line([10, 10, 110, 40], "Hello  world"), line([10, 50, 60, 80], "Second")])
    root, text = page_to_tree(p, (200, 100), 200.0, page_number=3)
    assert root.ocr_class == OcrClass.PAGE and root.page_number == 3 and root.dpi == 200.0
    assert text == "Hello world\nSecond"
    assert [w.text for w in root.words] == ["Hello", "world", "Second"]
    assert len(root.lines) == 2


def test_blocks_group_lines_into_paragraphs_and_label_lines():
    blocks = [
        {"label": "Page-Header", "bbox": [0, 0, 200, 40], "text": "H"},
        {"label": "Text", "bbox": [0, 40, 200, 200], "text": "x"},
    ]
    p = page(
        [
            line([10, 5, 100, 30], "Header"),
            line([10, 50, 100, 70], "one"),
            line([10, 75, 100, 95], "two"),
        ],
        blocks,
    )
    root, _ = page_to_tree(p, (300, 300), 300.0)
    pars = root.paragraphs
    assert [len(x.children) for x in pars] == [1, 2]
    assert pars[0].children[0].ocr_class == OcrClass.HEADER
    assert pars[1].children[0].ocr_class == OcrClass.LINE


def test_empty_and_degenerate_lines_are_dropped():
    p = page([line([0, 0, 10, 10], "   "), line([5, 5, 5, 20], "zero width")])
    root, text = page_to_tree(p, (50, 50), 72.0)
    assert text == "" and root.words == []


def test_boxes_are_clamped_to_the_page():
    p = page([line([-5, -5, 500, 30], "wide")])
    root, _ = page_to_tree(p, (100, 100), 72.0)
    b = root.lines[0].bbox
    assert (b.left, b.top, b.right) == (0, 0, 100)


def test_to_input_frame_roundtrip():
    # input 100 wide x 50 tall, content turned counter-clockwise once, so the upright
    # page is 50 wide x 100 tall. A box at the upright top-left lands at the input's
    # bottom-left after one counter-clockwise quarter turn.
    assert to_input_frame([0, 0, 10, 20], 1, (50, 100)) == [0, 40, 20, 50]
    assert to_input_frame([1, 2, 3, 4], 0, (50, 100)) == [1, 2, 3, 4]
    # two turns = 180 degrees
    assert to_input_frame([0, 0, 10, 20], 2, (100, 50)) == [90, 30, 100, 50]


def test_rotated_page_is_mapped_back_to_input_frame():
    p = page([line([0, 0, 10, 20], "up")], rotation=90)
    root, _ = page_to_tree(p, (100, 50), 72.0)
    b = root.lines[0].bbox
    assert (b.left, b.top, b.right, b.bottom) == (0, 40, 20, 50)


def test_latin_lookalikes_become_cyrillic_on_a_cyrillic_page(monkeypatch):
    monkeypatch.delenv("INDRA_SCRIPT_FIX", raising=False)
    lines = [
        line([0, 0, 90, 10], "Основание: Плановая проверка"),
        line([0, 20, 90, 30], "Aдрес COO CE 4"),  # first letter is Latin
    ]
    _, text = page_to_tree(page(lines), (100, 100), 200.0)
    # mixed word and all-lookalike word are converted, short "CE" and "4" are kept
    assert text.splitlines()[1] == "Адрес СОО CE 4"


def test_english_page_is_left_alone(monkeypatch):
    monkeypatch.delenv("INDRA_SCRIPT_FIX", raising=False)
    lines = [line([0, 0, 90, 10], "Meter CEO Price kW")]
    _, text = page_to_tree(page(lines), (100, 100), 200.0)
    assert text == "Meter CEO Price kW"


def test_script_fix_can_be_switched_off(monkeypatch):
    monkeypatch.setenv("INDRA_SCRIPT_FIX", "off")
    lines = [line([0, 0, 90, 10], "Основание Plan"), line([0, 20, 90, 30], "COO")]
    _, text = page_to_tree(page(lines), (100, 100), 200.0)
    assert text.splitlines()[1] == "COO"
