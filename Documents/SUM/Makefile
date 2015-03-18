REFSIZE='\\small'

all: patty.pdf

patty.pdf: patty.tex *.tex
	pdflatex $<
	#bibtex  patty
	#perl -i -p -e 's|^(\\begin{thebibliography}{.*})$$|$$1\n\n'$(REFSIZE)'|' patty.bbl
	pdflatex $<
	pdflatex $<
	#dvipdf patty
	rm patty.aux patty.log 
	rm patty.blg patty.bbl patty.out patty.brf

clean:
	rm patty.pdf 
	rm patty.aux patty.log patty.blg patty.bbl 
