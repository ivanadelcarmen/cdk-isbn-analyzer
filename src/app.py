from pathlib import Path
from configparser import ConfigParser

import aws_cdk as cdk

from cdk.stack import isbnProcessorStack

config_file = Path(__file__).parent / 'config.conf'
parser = ConfigParser()
parser.read(config_file)

REGION = parser.get('deployOptions', 'region')

app = cdk.App()
isbnProcessorStack(app, 'cdk-isbn-analyzer', env=cdk.Environment(region=REGION))
app.synth()
