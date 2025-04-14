.PHONY: run

default: run

install:
	pip install graphviz

run:
	python3 ./main.py
	
ui:
	streamlit run interface/ui_app.py