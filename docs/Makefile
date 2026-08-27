DOC = elliptic-disk-model

all: $(DOC).pdf

$(DOC).pdf: $(DOC).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(DOC).tex
	pdflatex -interaction=nonstopmode -halt-on-error $(DOC).tex

clean:
	rm -f $(DOC).aux $(DOC).log $(DOC).toc $(DOC).out

distclean: clean
	rm -f $(DOC).pdf

.PHONY: all clean distclean
