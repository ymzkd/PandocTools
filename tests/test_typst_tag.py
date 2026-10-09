"""Pandoc の実際の TeX→Typst 変換を通す式番号の回帰テスト。"""
from pathlib import Path
import shutil
import subprocess

import pytest


FILTERS = Path(__file__).resolve().parent.parent / "src" / "filters"
pytestmark = pytest.mark.skipif(not shutil.which("pandoc"), reason="pandoc is required")


def convert(source, *, crossref=False):
    args = ["pandoc", "-f", "markdown", "-t", "typst"]
    if crossref:
        args += ["--filter", "pandoc-crossref", "-M", "linkReferences=true"]
    args += ["--lua-filter", str(FILTERS / "typst_crossref_tag.lua"),
             "--lua-filter", str(FILTERS / "typst_tag.lua")]
    result = subprocess.run(args, input=source, capture_output=True, encoding="utf-8", check=True)
    assert "Could not convert TeX math" not in result.stderr
    return result.stdout


@pytest.mark.parametrize("env", ["align*", "align", "aligned", "gather*", "gathered"])
def test_each_row_keeps_its_tag(env):
    source = r"""$$
\begin{ENV}
a = b \tag{2a} \\
c = d \tag{2b} \\
e = f \tag{2c}
\end{ENV}
$$""".replace("ENV", env)
    output = convert(source)
    for tag in ("2a", "2b", "2c"):
        assert output.count(f'"({tag})"') == 1
    assert output.count('#import "@preview/equate:0.3.2"') == 1
    assert "($ " in output and "$).body" in output


def test_nested_rows_and_unnumbered_row_do_not_shift_tags():
    source = r"""$$
\begin{align*}
A &= \begin{bmatrix} 1 & 2 \\ 3 & 4 \end{bmatrix} \tag{A} \\
b &= \begin{cases} 1 & x > 0 \\ 0 & x < 0 \end{cases} \nonumber \\
c &= \frac{d}{e} \tag{C}
\end{align*}
$$"""
    output = convert(source)
    assert '("(A)", [], "(C)",)' in output
    assert "mat(" in output and "cases(" in output


def test_single_block_tag_keeps_original_path():
    output = convert(r"$$\begin{aligned} a &= b \\ c &= d \end{aligned} \tag{T}$$")
    assert 'numbering: _ => "(T)"' in output
    assert "equate" not in output


def test_tags_with_latex_and_comments():
    output = convert(r"""$$
\begin{align*}
a &= 1 \tag{\ast} \\ % \tag{wrong} \\
b &= 2 \tag{B}
\end{align*}
$$""")
    assert '[($*$)]' in output
    assert '"(B)"' in output
    assert "wrong" not in output


@pytest.mark.skipif(not shutil.which("typst"), reason="typst is required")
def test_pdf_tags_align_with_rows_and_crossref_survives(tmp_path):
    fitz = pytest.importorskip("fitz")
    if not shutil.which("pandoc-crossref"):
        pytest.skip("pandoc-crossref is required")
    source = r"""$$
\begin{align*}
a &= b \tag{2a} \\
c &= \frac{d}{e} \tag{2b} \\
x &= \begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix} \tag{2c}
\end{align*}
$$ {#eq:rows}

See @eq:rows.

$$ f = g \tag{single} $$

$$
\begin{align*}
m &= n \tag{M} \\
p &= q \tag{P}
\end{align*}
$$
"""
    output = convert(source, crossref=True)
    assert output.count('#import "@preview/equate:0.3.2"') == 1
    assert 'id: "eq:rows"' in output
    typ = tmp_path / "tags.typ"
    pdf = tmp_path / "tags.pdf"
    typ.write_text('#set page(width: 180mm, height: auto, margin: 15mm)\n'
                   '#set text(size: 14pt)\n' + output, encoding="utf-8")
    subprocess.run(["typst", "compile", str(typ), str(pdf)], capture_output=True,
                   encoding="utf-8", check=True)
    with fitz.open(pdf) as doc:
        page = doc[0]
        # Text origins give baselines even when fractions and matrices have different heights.
        spans = [s for b in page.get_text("dict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"]]
        chars = [c for b in page.get_text("rawdict")["blocks"] if "lines" in b
                 for line in b["lines"] for s in line["spans"] for c in s["chars"]]
        equals = [c["origin"] for c in chars if c["c"] == "="]
        assert len(equals) == 6
        assert max(x for x, _ in equals[:3]) - min(x for x, _ in equals[:3]) < 0.1
        for index, tag in enumerate(("(2a)", "(2b)", "(2c)")):
            number = next(s for s in spans if s["text"] == tag)
            assert abs(number["origin"][1] - equals[index][1]) < 0.1
            assert number["bbox"][2] == pytest.approx(page.rect.width - 15 * 72 / 25.4, abs=0.1)
        text = page.get_text()
        assert "(single)" in text and "(M)" in text and "(P)" in text
        assert any(link["kind"] == fitz.LINK_GOTO for link in page.get_links())
