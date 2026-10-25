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

    def test_italic_span_becomes_em(self):
        self.assertEqual(
            render_inline("an *italic* word"), "an <em>italic</em> word"
        )

    def test_bold_and_italic_compose(self):
        self.assertEqual(
            render_inline("**bold** and *italic*"),
            "<strong>bold</strong> and <em>italic</em>",
        )

    def test_italic_does_not_touch_bold_runs(self):
        self.assertEqual(
            render_inline("**strong**"), "<strong>strong</strong>"
        )

    def test_italic_requires_non_space_flanks(self):
        self.assertEqual(render_inline("a * b * c"), "a * b * c")

    def test_lone_single_marker_is_literal(self):
        self.assertEqual(render_inline("5 * 6 = 30"), "5 * 6 = 30")

    def test_italic_text_is_escaped(self):
        self.assertEqual(
            render_inline("*<b>*"), "<em>&lt;b&gt;</em>"
        )

    def test_external_link_gets_rel(self):
        self.assertEqual(
            render_inline("see [the site](https://example.com)"),
            'see <a href="https://example.com" rel="noopener noreferrer">the site</a>',
        )

    def test_internal_link_has_no_rel(self):
        self.assertEqual(
            render_inline("[projects](/projects/)"),
            '<a href="/projects/">projects</a>',
        )

    def test_anchor_and_mailto_links(self):
        self.assertEqual(
            render_inline("[top](#top) and [mail](mailto:a@b.com)"),
            '<a href="#top">top</a> and '
            '<a href="mailto:a@b.com" rel="noopener noreferrer">mail</a>',
        )

    def test_link_label_renders_inline_markup(self):
        self.assertEqual(
            render_inline("[a **bold** label](https://e.com)"),
            '<a href="https://e.com" rel="noopener noreferrer">'
            "a <strong>bold</strong> label</a>",
        )

    def test_javascript_url_is_left_literal(self):
        self.assertEqual(
            render_inline("[x](javascript:alert(1))"),
            "[x](javascript:alert(1))",
        )

    def test_data_url_is_left_literal(self):
        self.assertEqual(
            render_inline("[x](data:text/html,<script>)"),
            "[x](data:text/html,&lt;script&gt;)",
        )

    def test_protocol_relative_url_is_left_literal(self):
        self.assertEqual(
            render_inline("[x](//evil.com)"), "[x](//evil.com)"
        )

    def test_link_url_quotes_cannot_break_attribute(self):
        rendered = render_inline('[x](https://e.com/"onmouseover=y)')
        self.assertNotIn('"onmouseover', rendered)
        self.assertIn("&quot;onmouseover=y", rendered)


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

    def test_unordered_list_with_dash(self):
        self.assertEqual(
            render_block("- one\n- two\n- three"),
            "<ul><li>one</li><li>two</li><li>three</li></ul>",
        )

    def test_unordered_list_with_asterisk(self):
        self.assertEqual(
            render_block("* a\n* b"), "<ul><li>a</li><li>b</li></ul>"
        )

    def test_ordered_list(self):
        self.assertEqual(
            render_block("1. first\n2. second"),
            "<ol><li>first</li><li>second</li></ol>",
        )

    def test_list_items_render_inline_markup(self):
        self.assertEqual(
            render_block("- a **bold** item\n- an *italic* item"),
            "<ul><li>a <strong>bold</strong> item</li>"
            "<li>an <em>italic</em> item</li></ul>",
        )

    def test_list_item_text_is_escaped(self):
        self.assertEqual(
            render_block("- <script>"), "<ul><li>&lt;script&gt;</li></ul>"
        )

    def test_mixed_block_is_not_a_list(self):
        self.assertEqual(
            render_block("- a list line\nbut not this one"),
            "<p>- a list line\nbut not this one</p>",
        )

    def test_italic_paragraph_not_mistaken_for_list(self):
        self.assertEqual(
            render_block("*just italic text*"), "<p><em>just italic text</em></p>"
        )


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
