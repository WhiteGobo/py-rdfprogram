default:


.PHONY: test_pathfinder
test_pathfinder:
	python -m pathfinder.test_pathfinder

.PHONY: test_rdfloader
test_rdfloader:
	python -m rdfloader.test_rdfloader -v # -k test_anyedge

.PHONY: test_programloader
test_programloader:
	#python -m programloader.test_programloader
	python -m programloader.test

.PHONY: test_flowgraph
test_flowgraph:
	python -m pathfinder.lin_flowgraph_abstract.test -v --failfast

test:
	python -m unittest

documentation:
	cd docs && $(MAKE) html 
	# cd pathfinder/lin_flowgraph_abstract/ && $(MAKE) documentation

opendoc:
	xdg-open docs/build/html/index.html
	# xdg-open pathfinder/lin_flowgraph_abstract/docs/build/html/index.html


