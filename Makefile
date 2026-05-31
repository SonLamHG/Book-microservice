.PHONY: help download-datasets preprocess train-ai data-pipeline clean-raw

help:
	@echo "Targets:"
	@echo "  download-datasets  Pull Amazon Books Reviews from Kaggle into ai-service/data/raw/"
	@echo "  preprocess         Build product_corpus.jsonl / user_behavior.csv / graph_triples.csv / seed_data_books.sql"
	@echo "  train-ai           Train LSTM and write ai-service/data/lstm_weights.pt"
	@echo "  data-pipeline      Run download + preprocess + train-ai end-to-end"
	@echo "  clean-raw          Delete the raw Kaggle download (~1 GB)"

download-datasets:
	python -m scripts.download_datasets

preprocess:
	python -m scripts.preprocess

train-ai:
	cd ai-service && python -m app.lstm.train

data-pipeline: download-datasets preprocess train-ai

clean-raw:
	rm -rf ai-service/data/raw
