# Teach-back exercise - compute the capacity from raw readings

Give a reader the methodology write-up (without the worked example's result) and this table. Ask them to compute the share of the 256 front positions able to test over these readings, using only the written rules. The answer key is `python methodology_check.py --answer`; a reader who is within 0.1 point has understood the method.

| time | count | list |
|---|---|---|
| 10:00 | 22 | 1-22 |
| 10:04 | 22 | 1-22 |
| 10:08 | 256 | 1;1;1 |
| 10:12 | 24 | 1-24 |
| 10:16 | 252 | 1-24 |
| 10:20 | 30 | 1-22 |
| 10:24 | 24 | 1-24 |
| 10:44 | 24 | 1-24 |
| 10:48 | 24 | 1-23;600 |
