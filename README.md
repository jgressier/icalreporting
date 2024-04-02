icalreporting
-----

[![PyPi Version](https://img.shields.io/pypi/v/icalreporting.svg?style=flat)](https://pypi.org/project/icalreporting)
[![PyPI pyversions](https://img.shields.io/pypi/pyversions/icalreporting.svg?style=flat)](https://pypi.org/pypi/icalreporting/)
[![GitHub stars](https://img.shields.io/github/stars/jgressier/icalreporting.svg?style=flat&logo=github&label=Stars&logoColor=white)](https://github.com/jgressier/icalreporting)
[![PyPi downloads](https://img.shields.io/pypi/dm/icalreporting.svg?style=flat)](https://pypistats.org/packages/icalreporting)
[![codecov](https://img.shields.io/codecov/c/github/jgressier/icalreporting.svg?style=flat)](https://codecov.io/gh/jgressier/icalreporting)

[![Codacy Badge](https://app.codacy.com/project/badge/Grade/d32cf67a5fa242c88bb1568277f1d60e)](https://app.codacy.com/gh/jgressier/icalreporting/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade)[![Doc](https://readthedocs.org/projects/icalreporting/badge/?version=latest)](https://readthedocs.org/projects/icalreporting/)
[![Slack](https://img.shields.io/static/v1?logo=slack&label=slack&message=contact&style=flat)](https://join.slack.com/t/isae-opendev/shared_invite/zt-obqywf6r-UUuHR4_hc5iTzyL5bFCwpw
)

### Features

- able to load ical files and fill a pandas database
- parse the pandas database to identify project and creates a worksheet tables
- export to open document XLSX file

### Installation

```bash
pip install --upgrade icalreporting
```
This automatic installation will get needed dependencies. 

### Requirements

see [requirements.txt](https://github.com/jgressier/icalreporting/blob/master/requirements.txt)

### Usage

When installed, you just need to put a set a ical files in a folder for a project. You will be able to create a reporting file with the following lines.

```python
from icalreporting.reporting import Project
prj = Project(name="Big-Project", folder="examples/projectA", start="2023-01-01", end="2024-01-01")
prj.load_ics()  # read files
wb = prj.workbook()  # create workbook
wb.save("projectA.xlsx")  # save it to file
```