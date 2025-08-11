# **ISBN OLTP data repository using image analysis and NoSQL storage services in AWS**

_**Technology stack**: Python 3.12, `boto3`, Google Books API_ \
_**AWS services**: IAM, API Gateway, S3, Lambda, Amazon Rekognition, CloudWatch, DynamoDB_ \
_**IaC framework**: AWS Cloud Development Kit_

## Abstract

The following program fetches relevant book data from the Google Books API given ISBN numbers which are parsed from images stored in S3 —sent by users through an API Gateway endpoint— and analyzed in a Lambda Function with Amazon Rekognition support. The related data is processed altogether in Lambda to be structured and later logged into CloudWatch and stored into a DynamoDB table, useful for further analysis and ad hoc querying.

## Deployment

### Requirements

* Latest version of `pip` installed

* Configured AWS CLI profile with administrator permissions and a default region, set up by completing the prompt triggered by the following command:

    ```
    aws configure [--profile <profile_name>]
    ```

* Node.js 20.x or later installed (check current [Node.js versions supported by AWS CDK](https://docs.aws.amazon.com/cdk/v2/guide/node-versions.html))

* AWS CDK v2 `npm` package installed

* CDK bootstrapped in the AWS CLI profile by running the following command:
    ```
    cdk bootstrap [--profile <profile_name>]
    ```

## Architecture

![AWS architecture diagram](docs/diagram.png)