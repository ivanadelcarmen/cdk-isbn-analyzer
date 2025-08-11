# **ISBN OLTP data repository using image analysis and NoSQL storage services in AWS**

_**Technology stack**: Python 3.12, `boto3`, Google Books API_ \
_**AWS services**: IAM, API Gateway, S3, Lambda, Amazon Rekognition, CloudWatch, DynamoDB_ \
_**IaC framework**: AWS Cloud Development Kit_

## Abstract

The following program fetches relevant book data from the Google Books API given ISBN numbers which are parsed from images stored in S3 —sent by users through an API Gateway endpoint— and analyzed in a Lambda Function with Amazon Rekognition support. The related data is processed altogether in Lambda to be structured and later logged into CloudWatch and stored into a DynamoDB table, useful for further analysis and ad hoc querying.

## Architecture

![AWS architecture diagram](docs/diagram.png)