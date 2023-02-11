docker:
	docker build  . --tag pcc-mqtt

unittest:
	python3 -m unittest test/*.py