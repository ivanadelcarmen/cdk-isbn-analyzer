#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk.cdk_stack import isbnProcessorStack

app = cdk.App()
isbnProcessorStack(app, 'cdk-isbn-processor')
app.synth()
