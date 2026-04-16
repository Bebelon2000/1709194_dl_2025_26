from transformers import pipeline
classifier = pipeline("sentiment-analysis")
x=input("write a phrase")
print(classifier(x))