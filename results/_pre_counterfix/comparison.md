# Defense comparison

_One section per (dataset, partition). Attack scenarios show BSR/CA/DR/FPR/stealthiness per defense; a lower BSR and higher DR is better._

## dataset = `ciciot2023` | partition = `iid`

### Attack scenarios

| defense | variant | trigger | malicious_ratio | poison_rate | CA | BSR | DR | FPR | stealthiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fedavg | adaptive | fixed | 0.2000 | 0.1000 | 0.6971 | 0.9567 | nan | nan | nan |
| fedavg | constrained | fixed | 0.2000 | 0.1000 | 0.7214 | 0.9707 | nan | nan | nan |
| fedavg | decorrelated | fixed | 0.2000 | 0.1000 | 0.6904 | 0.9572 | nan | nan | nan |
| fedavg | simple | fixed | 0.1000 | 0.0500 | 0.6671 | 0.8992 | nan | nan | nan |
| fedavg | simple | fixed | 0.1000 | 0.1000 | 0.6638 | 0.9068 | nan | nan | nan |
| fedavg | simple | fixed | 0.1000 | 0.2000 | 0.6647 | 0.9288 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.0500 | 0.6938 | 0.9571 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.6991 | 0.9685 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.7139 | 0.9870 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.6826 | 0.9654 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.6940 | 0.9549 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.7097 | 0.9621 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.6883 | 0.9804 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.2000 | 0.7066 | 0.9992 | nan | nan | nan |
| fedavg | simple | fixed | 0.3000 | 0.0500 | 0.7203 | 0.9616 | nan | nan | nan |
| fedavg | simple | fixed | 0.3000 | 0.1000 | 0.6801 | 0.9997 | nan | nan | nan |
| fedavg | simple | fixed | 0.3000 | 0.2000 | 0.6782 | 0.9998 | nan | nan | nan |
| fedavg | simple | statistical | 0.1000 | 0.0500 | 0.6785 | 0.9984 | nan | nan | nan |
| fedavg | simple | statistical | 0.1000 | 0.1000 | 0.6938 | 0.9996 | nan | nan | nan |
| fedavg | simple | statistical | 0.1000 | 0.2000 | 0.6893 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.0500 | 0.7181 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.7340 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.7217 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.6857 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.7141 | 0.9998 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.7201 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.7172 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.2000 | 0.7015 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.3000 | 0.0500 | 0.7038 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.3000 | 0.1000 | 0.7139 | 1.0000 | nan | nan | nan |
| fedavg | simple | statistical | 0.3000 | 0.2000 | 0.6973 | 1.0000 | nan | nan | nan |
| fedavg | simple | temporal | 0.1000 | 0.0500 | 0.6894 | 0.9986 | nan | nan | nan |
| fedavg | simple | temporal | 0.1000 | 0.1000 | 0.6676 | 0.9999 | nan | nan | nan |
| fedavg | simple | temporal | 0.1000 | 0.2000 | 0.7167 | 0.9999 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.0500 | 0.6817 | 0.9993 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.6746 | 0.9997 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.7166 | 1.0000 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.6753 | 0.9999 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.7069 | 0.9999 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.7143 | 0.9996 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.6776 | 1.0000 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.2000 | 0.6885 | 0.9999 | nan | nan | nan |
| fedavg | simple | temporal | 0.3000 | 0.0500 | 0.6957 | 0.9997 | nan | nan | nan |
| fedavg | simple | temporal | 0.3000 | 0.1000 | 0.7093 | 1.0000 | nan | nan | nan |
| fedavg | simple | temporal | 0.3000 | 0.2000 | 0.6784 | 1.0000 | nan | nan | nan |
| flame | simple | fixed | 0.1000 | 0.0500 | 0.4917 | 0.0057 | 0.6500 | 0.4222 | 0.0020 |
| flame | simple | fixed | 0.1000 | 0.1000 | 0.5522 | 0.0090 | 0.5500 | 0.4389 | 0.0041 |
| flame | simple | fixed | 0.1000 | 0.2000 | 0.4417 | 0.0054 | 0.7500 | 0.4167 | 0.0013 |
| flame | simple | fixed | 0.2000 | 0.0500 | 0.4456 | 0.0347 | 0.4000 | 0.4625 | 0.0208 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.4044 | 0.0120 | 0.5250 | 0.4313 | 0.0057 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.5023 | 0.0146 | 0.7750 | 0.3625 | 0.0033 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.6590 | 0.0087 | 0.6750 | 0.3875 | 0.0028 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.6328 | 0.0067 | 0.7500 | 0.3750 | 0.0017 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.4929 | 0.0077 | 0.4500 | 0.4500 | 0.0043 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.4821 | 0.0059 | 0.5500 | 0.4250 | 0.0026 |
| flame | simple | fixed | 0.2000 | 0.2000 | 0.4441 | 0.0101 | 0.5250 | 0.4313 | 0.0048 |
| flame | simple | fixed | 0.3000 | 0.0500 | 0.4637 | 0.2320 | 0.4000 | 0.4643 | 0.1392 |
| flame | simple | fixed | 0.3000 | 0.1000 | 0.4266 | 0.0741 | 0.4167 | 0.4643 | 0.0432 |
| flame | simple | fixed | 0.3000 | 0.2000 | 0.4065 | 0.0558 | 0.4667 | 0.4429 | 0.0297 |
| flame | simple | statistical | 0.1000 | 0.0500 | 0.4457 | 0.7873 | 0.4500 | 0.4444 | 0.4330 |
| flame | simple | statistical | 0.1000 | 0.1000 | 0.5788 | 0.8441 | 0.3500 | 0.4611 | 0.5487 |
| flame | simple | statistical | 0.1000 | 0.2000 | 0.5095 | 0.6799 | 0.4500 | 0.4500 | 0.3739 |
| flame | simple | statistical | 0.2000 | 0.0500 | 0.5134 | 0.9499 | 0.4000 | 0.4625 | 0.5699 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.4112 | 0.8725 | 0.3500 | 0.4750 | 0.5671 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.4625 | 0.6360 | 0.5500 | 0.4250 | 0.2862 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.3887 | 0.8638 | 0.3500 | 0.4750 | 0.5614 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.5558 | 0.9709 | 0.4250 | 0.4562 | 0.5583 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.5022 | 0.9737 | 0.4250 | 0.4562 | 0.5599 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.5183 | 0.9780 | 0.3750 | 0.4688 | 0.6112 |
| flame | simple | statistical | 0.2000 | 0.2000 | 0.4505 | 0.9818 | 0.4250 | 0.4562 | 0.5645 |
| flame | simple | statistical | 0.3000 | 0.0500 | 0.4345 | 0.9503 | 0.4000 | 0.4714 | 0.5702 |
| flame | simple | statistical | 0.3000 | 0.1000 | 0.4413 | 0.9975 | 0.4500 | 0.4500 | 0.5486 |
| flame | simple | statistical | 0.3000 | 0.2000 | 0.4539 | 0.9856 | 0.4167 | 0.4643 | 0.5749 |
| flame | simple | temporal | 0.1000 | 0.0500 | 0.5855 | 0.0929 | 0.4000 | 0.4556 | 0.0558 |
| flame | simple | temporal | 0.1000 | 0.1000 | 0.5795 | 0.0243 | 0.4500 | 0.4444 | 0.0134 |
| flame | simple | temporal | 0.1000 | 0.2000 | 0.5309 | 0.5284 | 0.3500 | 0.4611 | 0.3435 |
| flame | simple | temporal | 0.2000 | 0.0500 | 0.5508 | 0.9174 | 0.3750 | 0.4688 | 0.5734 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.5129 | 0.9851 | 0.4000 | 0.4625 | 0.5911 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.5237 | 0.9201 | 0.5500 | 0.4250 | 0.4141 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.6129 | 0.9901 | 0.4000 | 0.4625 | 0.5940 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.5754 | 0.4643 | 0.4250 | 0.4562 | 0.2670 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.5544 | 0.9564 | 0.5000 | 0.4375 | 0.4782 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.4190 | 0.8215 | 0.3250 | 0.4813 | 0.5545 |
| flame | simple | temporal | 0.2000 | 0.2000 | 0.4107 | 0.9770 | 0.3750 | 0.4688 | 0.6107 |
| flame | simple | temporal | 0.3000 | 0.0500 | 0.4983 | 0.9902 | 0.4167 | 0.4643 | 0.5776 |
| flame | simple | temporal | 0.3000 | 0.1000 | 0.4554 | 0.9965 | 0.4333 | 0.4571 | 0.5647 |
| flame | simple | temporal | 0.3000 | 0.2000 | 0.4539 | 0.9989 | 0.4000 | 0.4714 | 0.5993 |
| fltrust | simple | fixed | 0.1000 | 0.0500 | 0.6435 | 0.0031 | 0.0000 | 0.0000 | 0.0031 |
| fltrust | simple | fixed | 0.1000 | 0.1000 | 0.5108 | 0.0037 | 0.0000 | 0.0000 | 0.0037 |
| fltrust | simple | fixed | 0.1000 | 0.2000 | 0.5275 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.0500 | 0.5081 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5093 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5885 | 0.0037 | 0.0000 | 0.0000 | 0.0037 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5364 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.6342 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5125 | 0.0036 | 0.0000 | 0.0000 | 0.0036 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5092 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5089 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.2000 | 0.2000 | 0.5065 | 0.0039 | 0.0000 | 0.0000 | 0.0039 |
| fltrust | simple | fixed | 0.3000 | 0.0500 | 0.5322 | 0.0038 | 0.0000 | 0.0000 | 0.0038 |
| fltrust | simple | fixed | 0.3000 | 0.1000 | 0.5033 | 0.0039 | 0.0000 | 0.0000 | 0.0039 |
| fltrust | simple | fixed | 0.3000 | 0.2000 | 0.4926 | 0.0040 | 0.0000 | 0.0000 | 0.0040 |
| fltrust | simple | statistical | 0.1000 | 0.0500 | 0.5187 | 0.0001 | 0.0000 | 0.0000 | 0.0001 |
| fltrust | simple | statistical | 0.1000 | 0.1000 | 0.5108 | 0.0001 | 0.0000 | 0.0000 | 0.0001 |
| fltrust | simple | statistical | 0.1000 | 0.2000 | 0.5093 | 0.0001 | 0.0000 | 0.0000 | 0.0001 |
| fltrust | simple | statistical | 0.2000 | 0.0500 | 0.5082 | 0.0003 | 0.0000 | 0.0000 | 0.0003 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.5091 | 0.0004 | 0.0000 | 0.0000 | 0.0004 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.5096 | 0.0004 | 0.0000 | 0.0000 | 0.0004 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.5817 | 0.0224 | 0.0000 | 0.0000 | 0.0224 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.6568 | 0.0005 | 0.0000 | 0.0000 | 0.0005 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.6258 | 0.0096 | 0.0000 | 0.0000 | 0.0096 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.5091 | 0.0004 | 0.0000 | 0.0000 | 0.0004 |
| fltrust | simple | statistical | 0.2000 | 0.2000 | 0.4897 | 0.0004 | 0.0000 | 0.0000 | 0.0004 |
| fltrust | simple | statistical | 0.3000 | 0.0500 | 0.5095 | 0.0027 | 0.0000 | 0.0000 | 0.0027 |
| fltrust | simple | statistical | 0.3000 | 0.1000 | 0.5091 | 0.0008 | 0.0000 | 0.0000 | 0.0008 |
| fltrust | simple | statistical | 0.3000 | 0.2000 | 0.4981 | 0.0008 | 0.0000 | 0.0000 | 0.0008 |
| fltrust | simple | temporal | 0.1000 | 0.0500 | 0.5113 | 0.0019 | 0.0000 | 0.0000 | 0.0019 |
| fltrust | simple | temporal | 0.1000 | 0.1000 | 0.5111 | 0.0031 | 0.0000 | 0.0000 | 0.0031 |
| fltrust | simple | temporal | 0.1000 | 0.2000 | 0.5080 | 0.0051 | 0.0000 | 0.0000 | 0.0051 |
| fltrust | simple | temporal | 0.2000 | 0.0500 | 0.5114 | 0.6924 | 0.0000 | 0.0000 | 0.6924 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.5001 | 0.8754 | 0.0000 | 0.0000 | 0.8754 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.5090 | 0.5621 | 0.0000 | 0.0000 | 0.5621 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.5105 | 0.6992 | 0.0000 | 0.0000 | 0.6992 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.6557 | 0.8923 | 0.0000 | 0.0000 | 0.8923 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.5127 | 0.8820 | 0.0000 | 0.0000 | 0.8820 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.5006 | 0.8746 | 0.0000 | 0.0000 | 0.8746 |
| fltrust | simple | temporal | 0.2000 | 0.2000 | 0.4946 | 0.8734 | 0.0000 | 0.0000 | 0.8734 |
| fltrust | simple | temporal | 0.3000 | 0.0500 | 0.4919 | 0.8868 | 0.0000 | 0.0000 | 0.8868 |
| fltrust | simple | temporal | 0.3000 | 0.1000 | 0.4934 | 0.8865 | 0.0000 | 0.0000 | 0.8865 |
| fltrust | simple | temporal | 0.3000 | 0.2000 | 0.4866 | 0.8882 | 0.0000 | 0.0000 | 0.8882 |
| foolsgold | simple | fixed | 0.2000 | 0.1000 | 0.6961 | 0.0262 | 0.7500 | 0.0000 | 0.0065 |
| foolsgold | simple | fixed | 0.2000 | 0.1000 | 0.6973 | 0.9262 | 0.0000 | 0.0000 | 0.9262 |
| foolsgold | simple | fixed | 0.2000 | 0.1000 | 0.6788 | 0.8816 | 0.5000 | 0.0000 | 0.4408 |
| foolsgold | simple | fixed | 0.2000 | 0.1000 | 0.7155 | 0.0078 | 0.5000 | 0.0000 | 0.0039 |
| foolsgold | simple | fixed | 0.2000 | 0.1000 | 0.7166 | 0.0031 | 0.5000 | 0.0000 | 0.0016 |
| foolsgold | simple | statistical | 0.2000 | 0.1000 | 0.7185 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| foolsgold | simple | statistical | 0.2000 | 0.1000 | 0.7327 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| foolsgold | simple | statistical | 0.2000 | 0.1000 | 0.6708 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| foolsgold | simple | statistical | 0.2000 | 0.1000 | 0.7250 | 0.9987 | 0.0000 | 0.0000 | 0.9987 |
| foolsgold | simple | statistical | 0.2000 | 0.1000 | 0.7164 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| foolsgold | simple | temporal | 0.2000 | 0.1000 | 0.7140 | 0.9999 | 0.0000 | 0.0000 | 0.9999 |
| foolsgold | simple | temporal | 0.2000 | 0.1000 | 0.7186 | 0.9997 | 0.0000 | 0.0000 | 0.9997 |
| foolsgold | simple | temporal | 0.2000 | 0.1000 | 0.6677 | 1.0000 | 0.0000 | 0.0000 | 1.0000 |
| foolsgold | simple | temporal | 0.2000 | 0.1000 | 0.7034 | 0.9999 | 0.0000 | 0.0000 | 0.9999 |
| foolsgold | simple | temporal | 0.2000 | 0.1000 | 0.6905 | 0.9999 | 0.0000 | 0.0000 | 0.9999 |
| gradcos | simple | fixed | 0.1000 | 0.0500 | 0.7041 | 0.0032 | 0.9000 | 0.0500 | 0.0003 |
| gradcos | simple | fixed | 0.1000 | 0.1000 | 0.6870 | 0.0058 | 0.9000 | 0.0389 | 0.0006 |
| gradcos | simple | fixed | 0.1000 | 0.2000 | 0.6811 | 0.0057 | 1.0000 | 0.0222 | 0.0000 |
| gradcos | simple | fixed | 0.2000 | 0.0500 | 0.7144 | 0.4821 | 0.5750 | 0.0250 | 0.2049 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.6733 | 0.0042 | 0.9500 | 0.0000 | 0.0002 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.6974 | 0.0007 | 0.9750 | 0.0125 | 0.0000 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.7034 | 0.0026 | 0.9500 | 0.0000 | 0.0001 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.7063 | 0.0075 | 0.9750 | 0.0125 | 0.0002 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.7180 | 0.0053 | 0.9750 | 0.0000 | 0.0001 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.6945 | 0.0059 | 0.9750 | 0.0000 | 0.0001 |
| gradcos | simple | fixed | 0.2000 | 0.2000 | 0.6664 | 0.0045 | 1.0000 | 0.0000 | 0.0000 |
| gradcos | simple | fixed | 0.3000 | 0.0500 | 0.6853 | 0.9460 | 0.1000 | 0.1214 | 0.8514 |
| gradcos | simple | fixed | 0.3000 | 0.1000 | 0.7163 | 0.0783 | 0.7833 | 0.0000 | 0.0170 |
| gradcos | simple | fixed | 0.3000 | 0.2000 | 0.7096 | 0.0040 | 1.0000 | 0.0000 | 0.0000 |
| gradcos | simple | statistical | 0.1000 | 0.0500 | 0.6862 | 0.9964 | 0.1000 | 0.0833 | 0.8967 |
| gradcos | simple | statistical | 0.1000 | 0.1000 | 0.6837 | 0.9778 | 0.1500 | 0.1444 | 0.8311 |
| gradcos | simple | statistical | 0.1000 | 0.2000 | 0.6814 | 0.0638 | 1.0000 | 0.0389 | 0.0000 |
| gradcos | simple | statistical | 0.2000 | 0.0500 | 0.7203 | 1.0000 | 0.0750 | 0.1187 | 0.9250 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.7101 | 0.9996 | 0.0250 | 0.1187 | 0.9746 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.7038 | 0.9996 | 0.1000 | 0.1000 | 0.8997 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.6859 | 0.9998 | 0.1250 | 0.0813 | 0.8748 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.7292 | 0.9995 | 0.1250 | 0.1187 | 0.8746 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.7084 | 0.9997 | 0.1500 | 0.1625 | 0.8497 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.7172 | 1.0000 | 0.0750 | 0.0813 | 0.9250 |
| gradcos | simple | statistical | 0.2000 | 0.2000 | 0.6742 | 0.9999 | 0.1000 | 0.0938 | 0.9000 |
| gradcos | simple | statistical | 0.3000 | 0.0500 | 0.6904 | 1.0000 | 0.0667 | 0.1500 | 0.9333 |
| gradcos | simple | statistical | 0.3000 | 0.1000 | 0.6934 | 1.0000 | 0.0833 | 0.1643 | 0.9167 |
| gradcos | simple | statistical | 0.3000 | 0.2000 | 0.6762 | 0.9992 | 0.0833 | 0.1286 | 0.9160 |
| gradcos | simple | temporal | 0.1000 | 0.0500 | 0.6679 | 0.9976 | 0.0500 | 0.1167 | 0.9477 |
| gradcos | simple | temporal | 0.1000 | 0.1000 | 0.7007 | 0.9996 | 0.0500 | 0.0944 | 0.9496 |
| gradcos | simple | temporal | 0.1000 | 0.2000 | 0.6988 | 0.9975 | 0.2000 | 0.0778 | 0.7980 |
| gradcos | simple | temporal | 0.2000 | 0.0500 | 0.6952 | 0.9990 | 0.1750 | 0.1000 | 0.8242 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.6891 | 0.9998 | 0.0750 | 0.1625 | 0.9248 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.7314 | 0.9999 | 0.1750 | 0.0938 | 0.8249 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.6806 | 0.9996 | 0.1500 | 0.1125 | 0.8496 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.7241 | 0.9999 | 0.1000 | 0.1062 | 0.8999 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.7049 | 1.0000 | 0.1750 | 0.1187 | 0.8250 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.6713 | 0.9998 | 0.1000 | 0.1125 | 0.8998 |
| gradcos | simple | temporal | 0.2000 | 0.2000 | 0.6977 | 0.9999 | 0.1750 | 0.1000 | 0.8249 |
| gradcos | simple | temporal | 0.3000 | 0.0500 | 0.6967 | 0.9999 | 0.0833 | 0.1286 | 0.9166 |
| gradcos | simple | temporal | 0.3000 | 0.1000 | 0.7013 | 1.0000 | 0.0500 | 0.1143 | 0.9500 |
| gradcos | simple | temporal | 0.3000 | 0.2000 | 0.6852 | 1.0000 | 0.1667 | 0.1000 | 0.8333 |
| krum | adaptive | fixed | 0.2000 | 0.1000 | 0.6918 | 0.0010 | 1.0000 | 0.0000 | 0.0000 |
| krum | decorrelated | fixed | 0.2000 | 0.1000 | 0.6918 | 0.0010 | 1.0000 | 0.0000 | 0.0000 |
| krum | simple | fixed | 0.1000 | 0.0500 | 0.7124 | 0.0014 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | fixed | 0.1000 | 0.1000 | 0.6948 | 0.0033 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | fixed | 0.1000 | 0.2000 | 0.7022 | 0.0026 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | fixed | 0.2000 | 0.0500 | 0.6693 | 0.9526 | 0.1250 | 0.2188 | 0.8335 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6870 | 0.9540 | 0.1500 | 0.2125 | 0.8109 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6986 | 0.9467 | 0.2000 | 0.2000 | 0.7574 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.7054 | 0.9404 | 0.2250 | 0.1938 | 0.7288 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6864 | 0.9274 | 0.1250 | 0.2188 | 0.8114 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6863 | 0.9700 | 0.2250 | 0.1938 | 0.7518 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6904 | 0.9597 | 0.1500 | 0.2125 | 0.8157 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6787 | 0.9653 | 0.1250 | 0.2188 | 0.8447 |
| krum | simple | fixed | 0.2000 | 0.2000 | 0.6766 | 0.1495 | 0.6500 | 0.0875 | 0.0523 |
| krum | simple | fixed | 0.3000 | 0.0500 | 0.6888 | 0.9591 | 0.0667 | 0.2571 | 0.8952 |
| krum | simple | fixed | 0.3000 | 0.1000 | 0.7104 | 0.9947 | 0.1333 | 0.2286 | 0.8621 |
| krum | simple | fixed | 0.3000 | 0.2000 | 0.7308 | 0.9997 | 0.1833 | 0.2071 | 0.8165 |
| krum | simple | statistical | 0.1000 | 0.0500 | 0.6852 | 0.8171 | 0.5000 | 0.1667 | 0.4085 |
| krum | simple | statistical | 0.1000 | 0.1000 | 0.7076 | 0.3705 | 0.9000 | 0.1222 | 0.0371 |
| krum | simple | statistical | 0.1000 | 0.2000 | 0.6987 | 0.0036 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | statistical | 0.2000 | 0.0500 | 0.6735 | 1.0000 | 0.0750 | 0.2313 | 0.9250 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.6871 | 1.0000 | 0.2250 | 0.1938 | 0.7750 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.6907 | 1.0000 | 0.2250 | 0.1938 | 0.7750 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.6950 | 0.9999 | 0.2250 | 0.1938 | 0.7749 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.7142 | 0.9989 | 0.2000 | 0.2000 | 0.7991 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.7002 | 0.9999 | 0.3250 | 0.1688 | 0.6750 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.6739 | 1.0000 | 0.1750 | 0.2062 | 0.8250 |
| krum | simple | statistical | 0.2000 | 0.2000 | 0.6644 | 1.0000 | 0.1500 | 0.2125 | 0.8500 |
| krum | simple | statistical | 0.3000 | 0.0500 | 0.6987 | 1.0000 | 0.1833 | 0.2071 | 0.8167 |
| krum | simple | statistical | 0.3000 | 0.1000 | 0.7070 | 1.0000 | 0.2333 | 0.1857 | 0.7667 |
| krum | simple | statistical | 0.3000 | 0.2000 | 0.6825 | 1.0000 | 0.1000 | 0.2429 | 0.9000 |
| krum | simple | temporal | 0.1000 | 0.0500 | 0.6941 | 0.0003 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | temporal | 0.1000 | 0.1000 | 0.6817 | 0.0022 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | temporal | 0.1000 | 0.2000 | 0.6757 | 0.0357 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | temporal | 0.2000 | 0.0500 | 0.6860 | 0.9993 | 0.1500 | 0.2125 | 0.8494 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.6795 | 0.9999 | 0.1750 | 0.2062 | 0.8249 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.7066 | 0.9999 | 0.2750 | 0.1812 | 0.7249 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.7114 | 1.0000 | 0.1500 | 0.2125 | 0.8500 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.7042 | 0.9999 | 0.2250 | 0.1938 | 0.7749 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.6906 | 0.9999 | 0.1500 | 0.2125 | 0.8499 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.6802 | 0.9998 | 0.1750 | 0.2062 | 0.8248 |
| krum | simple | temporal | 0.2000 | 0.2000 | 0.6731 | 0.9999 | 0.1750 | 0.2062 | 0.8249 |
| krum | simple | temporal | 0.3000 | 0.0500 | 0.6929 | 0.9996 | 0.1167 | 0.2357 | 0.8830 |
| krum | simple | temporal | 0.3000 | 0.1000 | 0.6843 | 0.9999 | 0.1333 | 0.2286 | 0.8666 |
| krum | simple | temporal | 0.3000 | 0.2000 | 0.6869 | 1.0000 | 0.2333 | 0.1857 | 0.7667 |

### Clean baselines

| defense | CA | macro_f1 |
| --- | --- | --- |
| fedavg | 0.6766 | 0.5542 |
| fedavg | 0.6995 | 0.5696 |
| fedavg | 0.6924 | 0.5533 |
| fedavg | 0.7203 | 0.5606 |
| fedavg | 0.7209 | 0.5650 |
| fedavg | 0.7036 | 0.5573 |
| fedavg | 0.6995 | 0.5657 |
| fedavg | 0.6995 | 0.5582 |
| flame | 0.4702 | 0.3102 |
| flame | 0.4870 | 0.3289 |
| flame | 0.5934 | 0.3618 |
| flame | 0.4965 | 0.3360 |
| flame | 0.4478 | 0.3308 |
| flame | 0.5502 | 0.3335 |
| fltrust | 0.5137 | 0.4131 |
| fltrust | 0.5196 | 0.4147 |
| fltrust | 0.5863 | 0.4383 |
| fltrust | 0.6467 | 0.4485 |
| fltrust | 0.5126 | 0.4151 |
| fltrust | 0.5144 | 0.4132 |
| fltrust | 0.5135 | 0.4131 |
| foolsgold | 0.6838 | 0.5542 |
| foolsgold | 0.7133 | 0.5596 |
| foolsgold | 0.6795 | 0.5548 |
| foolsgold | 0.7124 | 0.5633 |
| foolsgold | 0.7255 | 0.5679 |
| gradcos | 0.6980 | 0.5598 |
| gradcos | 0.6995 | 0.5687 |
| gradcos | 0.7024 | 0.5563 |
| gradcos | 0.7095 | 0.5621 |
| gradcos | 0.7162 | 0.5641 |
| gradcos | 0.7086 | 0.5491 |
| krum | 0.7037 | 0.5639 |
| krum | 0.7056 | 0.5663 |
| krum | 0.6772 | 0.5417 |
| krum | 0.7077 | 0.5662 |
| krum | 0.7186 | 0.5636 |
| krum | 0.6859 | 0.5424 |
| krum | 0.6857 | 0.5407 |

## dataset = `ciciot2023` | partition = `dirichlet`

### Attack scenarios

| defense | variant | trigger | malicious_ratio | poison_rate | CA | BSR | DR | FPR | stealthiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.7655 | 0.7915 | nan | nan | nan |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.5589 | 0.0140 | 0.5750 | 0.4188 | 0.0059 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.5028 | 0.0700 | 0.0000 | 0.0000 | 0.0700 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.7730 | 0.0041 | 0.4750 | 0.2125 | 0.0022 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.6359 | 0.9257 | 0.0000 | 0.2500 | 0.9257 |

### Clean baselines

| defense | CA | macro_f1 |
| --- | --- | --- |
| fedavg | 0.7771 | 0.5270 |
| flame | 0.5189 | 0.2921 |
| fltrust | 0.5080 | 0.4153 |
| gradcos | 0.7845 | 0.5310 |
| krum | 0.6704 | 0.5237 |

## dataset = `flnet2023` | partition = `iid`

### Attack scenarios

| defense | variant | trigger | malicious_ratio | poison_rate | CA | BSR | DR | FPR | stealthiness |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fedavg | simple | fixed | 0.1000 | 0.1000 | 0.9997 | 0.0068 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.0500 | 0.9995 | 0.9982 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.1000 | 0.9996 | 0.9981 | nan | nan | nan |
| fedavg | simple | fixed | 0.2000 | 0.2000 | 0.9997 | 0.9995 | nan | nan | nan |
| fedavg | simple | fixed | 0.3000 | 0.1000 | 0.9997 | 0.9994 | nan | nan | nan |
| fedavg | simple | statistical | 0.2000 | 0.1000 | 0.9997 | 0.4550 | nan | nan | nan |
| fedavg | simple | temporal | 0.2000 | 0.1000 | 0.9997 | 0.5666 | nan | nan | nan |
| flame | simple | fixed | 0.1000 | 0.1000 | 0.8680 | 0.0228 | 1.0000 | 0.3778 | 0.0000 |
| flame | simple | fixed | 0.2000 | 0.0500 | 0.8903 | 0.0231 | 1.0000 | 0.3063 | 0.0000 |
| flame | simple | fixed | 0.2000 | 0.1000 | 0.8133 | 0.0167 | 1.0000 | 0.3125 | 0.0000 |
| flame | simple | fixed | 0.2000 | 0.2000 | 0.8065 | 0.0234 | 1.0000 | 0.3125 | 0.0000 |
| flame | simple | fixed | 0.3000 | 0.1000 | 0.8237 | 0.0283 | 1.0000 | 0.2071 | 0.0000 |
| flame | simple | statistical | 0.2000 | 0.1000 | 0.8438 | 0.0281 | 1.0000 | 0.2938 | 0.0000 |
| flame | simple | temporal | 0.2000 | 0.1000 | 0.8299 | 0.0190 | 1.0000 | 0.3125 | 0.0000 |
| fltrust | simple | fixed | 0.1000 | 0.1000 | 0.9641 | 0.0159 | 0.0000 | 0.0000 | 0.0159 |
| fltrust | simple | fixed | 0.2000 | 0.0500 | 0.9642 | 0.0157 | 0.0000 | 0.0000 | 0.0157 |
| fltrust | simple | fixed | 0.2000 | 0.1000 | 0.9641 | 0.0158 | 0.0000 | 0.0000 | 0.0158 |
| fltrust | simple | fixed | 0.2000 | 0.2000 | 0.9641 | 0.0160 | 0.0000 | 0.0000 | 0.0160 |
| fltrust | simple | fixed | 0.3000 | 0.1000 | 0.9640 | 0.0161 | 0.0000 | 0.0000 | 0.0161 |
| fltrust | simple | statistical | 0.2000 | 0.1000 | 0.9641 | 0.0161 | 0.0000 | 0.0000 | 0.0161 |
| fltrust | simple | temporal | 0.2000 | 0.1000 | 0.9642 | 0.0160 | 0.0000 | 0.0000 | 0.0160 |
| gradcos | simple | fixed | 0.1000 | 0.1000 | 0.9997 | 0.0074 | 0.7000 | 0.0500 | 0.0022 |
| gradcos | simple | fixed | 0.2000 | 0.0500 | 0.9997 | 0.0075 | 0.7000 | 0.0375 | 0.0022 |
| gradcos | simple | fixed | 0.2000 | 0.1000 | 0.9995 | 0.9809 | 0.0750 | 0.1062 | 0.9073 |
| gradcos | simple | fixed | 0.2000 | 0.2000 | 0.9997 | 0.0075 | 0.9750 | 0.0000 | 0.0002 |
| gradcos | simple | fixed | 0.3000 | 0.1000 | 0.9997 | 0.9994 | 0.0333 | 0.1143 | 0.9661 |
| gradcos | simple | statistical | 0.2000 | 0.1000 | 0.9997 | 0.0012 | 0.5250 | 0.0563 | 0.0006 |
| gradcos | simple | temporal | 0.2000 | 0.1000 | 0.9997 | 0.0072 | 0.3750 | 0.0125 | 0.0045 |
| krum | simple | fixed | 0.1000 | 0.1000 | 0.9997 | 0.0075 | 1.0000 | 0.1111 | 0.0000 |
| krum | simple | fixed | 0.2000 | 0.0500 | 0.9997 | 0.0064 | 1.0000 | 0.0000 | 0.0000 |
| krum | simple | fixed | 0.2000 | 0.1000 | 0.9997 | 0.0074 | 1.0000 | 0.0000 | 0.0000 |
| krum | simple | fixed | 0.2000 | 0.2000 | 0.9997 | 0.0072 | 1.0000 | 0.0000 | 0.0000 |
| krum | simple | fixed | 0.3000 | 0.1000 | 0.9997 | 0.9992 | 0.3167 | 0.1500 | 0.6828 |
| krum | simple | statistical | 0.2000 | 0.1000 | 0.9997 | 0.0000 | 1.0000 | 0.0000 | 0.0000 |
| krum | simple | temporal | 0.2000 | 0.1000 | 0.9997 | 0.0065 | 1.0000 | 0.0000 | 0.0000 |

### Clean baselines

| defense | CA | macro_f1 |
| --- | --- | --- |
| fedavg | 0.9996 | 0.9995 |
| flame | 0.8888 | 0.5743 |
| fltrust | 0.9642 | 0.5963 |
| gradcos | 0.9997 | 0.9996 |
| krum | 0.9997 | 0.9992 |

