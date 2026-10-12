import unittest

from mdrender import render_block, render_body, render_inline


class RenderInlineTests(unittest.TestCase):
    def test_bold_span_becomes_strong(self):
        self.assertEqual(
            render_inline("a **bold** word"), "a <strong>bold</strong> word"
        )

    def test_multiple_bold_spans(self):
        self.assertEqual(
            render_inline("**one** and **two**"),
            "<strong>one</strong> and <strong>two</strong>",
        )

    def test_text_is_escaped_before_markup(self):
        self.assertEqual(
            render_inline("<script> & **x**"),
            "&lt;script&gt; &amp; <strong>x</strong>",
        )

    def test_lone_markers_are_left_literal(self):
        self.assertEqual(render_inline("2 ** 3 and ****"), "2 ** 3 and ****")


class RenderBlockTests(unittest.TestCase):
    def test_plain_block_becomes_paragraph(self):
        self.assertEqual(render_block("Hello there"), "<p>Hello there</p>")

    def test_heading_levels_one_through_six(self):
        for level in range(1, 7):
            hashes = "#" * level
            self.assertEqual(
                render_block(f"{hashes} Title"),
                f"<h{level}>Title</h{level}>",
            )

    def test_heading_allows_bold_inline(self):
        self.assertEqual(
            render_block("## A **key** point"),
            "<h2>A <strong>key</strong> point</h2>",
        )

    def test_optional_closing_hashes_are_trimmed(self):
        self.assertEqual(render_block("## Title ##"), "<h2>Title</h2>")

    def test_seven_hashes_is_not_a_heading(self):
        self.assertEqual(
            render_block("####### Too deep"), "<p>####### Too deep</p>"
        )

    def test_hash_without_space_is_not_a_heading(self):
        self.assertEqual(render_block("#nothashtag"), "<p>#nothashtag</p>")


class RenderBodyTests(unittest.TestCase):
    def test_blocks_render_in_order(self):
        self.assertEqual(
            render_body(["## Heading", "A **bold** line.", "Plain line."]),
            "<h2>Heading</h2><p>A <strong>bold</strong> line.</p><p>Plain line.</p>",
        )

    def test_empty_iterable_renders_nothing(self):
        self.assertEqual(render_body([]), "")


if __name__ == "__main__":
    unittest.main()
