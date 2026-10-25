LATEXMK ?= latexmk
DOCUMENT = response_matrices

.PHONY: all pdf clean

all: pdf

pdf: $(DOCUMENT).pdf

$(DOCUMENT).pdf: $(DOCUMENT).tex Makefile
	$(LATEXMK) -pdf -interaction=nonstopmode -halt-on-error -file-line-error $(DOCUMENT).tex

clean:
	$(LATEXMK) -c $(DOCUMENT).tex
