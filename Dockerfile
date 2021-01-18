###  bert-as-service has occasional issues with tensorflow > 2.0
FROM tensorflow/tensorflow:1.15.5-gpu

### Download base BERT-model
RUN curl https://storage.googleapis.com/bert_models/2020_02_20/uncased_L-12_H-768_A-12.zip \
    && unzip uncased_L-12_H-768_A-12.zip tmp/model/

### install bert-as-service server
RUN pip install update && pip install bert-serving-server

### Start server 
CMD [ "bert-serving-start", "-model_dir=tmp/model/uncased_L-12_H-768_A-12" ]