---
title: "Cores with FPU and its performance"
date: "2025-10-30"
# If default Espressif author is needed, uncomment this
# showAuthor: true
# Add a summary
summary: "This articles shows which cores have the FPU and what does it mean in terms of computational speed."
# Create your author entry (for details, see https://developer.espressif.com/pages/contribution-guide/writing-content/#add-youself-as-an-author)
#  - Create your page at `content/authors/<author-name>/_index.md`
#  - Add your personal data at `data/authors/<author-name>.json`
#  - Add author name(s) below
authors:
  - "alberto-spagnolo" # same as in the file paths above
  - "francesco-bez" # same as in the file paths above
# Add tags
tags: ["ESP32-C3", "ESP32-S3","performance", "FPU"]
---

__ESP32__

| Type   | Sum Cycles | Division Cycles |
|--------|------------|----------------|
| Double | 1336       | 1189           |
| Float  | 1526       | 2595           |
| Int    | 644        | 12             |



__ESP32-C3__

| Type   | Sum Cycles | Division Cycles |
|--------|------------|----------------|
| Double | 273        | 617            |
| Float  | 418        | 332            |
| Int    | 96         | 176            |


__ESP32-S3__

| Type   | Sum Cycles | Division Cycles |
|--------|------------|----------------|
| Double | 719        | 807            |
| Float  | 417        | 346            |
| Int    | 210        | 159            |



## Averaged cycles

__ESP32__

| Type   | Sum average (cycles) | Division average (cycles) |
| ------ | -------------------- | ------------------------- |
| DOUBLE | 77                   | 564                       |
| FLOAT  | 18                   | 57                        |
| INT    | 15                   | 18                        |

__ESP32C3__

| Type   | Sum average (cycles) | Division average (cycles) |
| ------ | -------------------- | ------------------------- |
| DOUBLE | 127                  | 399                       |
| FLOAT  | 105                  | 206                       |
| INT    | 10                   | 17                        |

__ESP32S3__

| Type   | Sum average (cycles) | Division average (cycles) |
| ------ | -------------------- | ------------------------- |
| DOUBLE | 75                   | 514                       |
| FLOAT  | 16                   | 62                        |
| INT    | 12                   | 15                        |


## Averaged time


ESP32

| Type   | Sum average (usec) | Division average (usec) |
| ------ | ------------------ | ----------------------- |
| DOUBLE | 0.47               | 3.54                    |
| FLOAT  | 0.11               | 0.37                    |
| INT    | 0.09               | 0.11                    |


ESP32C3

| Type   | Sum average (usec) | Division average (usec) |
| ------ | ------------------ | ----------------------- |
| DOUBLE | 0.79               | 2.50                    |
| FLOAT  | 0.66               | 1.29                    |
| INT    | 0.06               | 0.11                    |


ESP32S3

| Type   | Sum average (usec) | Division average (usec) |
| ------ | ------------------ | ----------------------- |
| DOUBLE | 0.47               | 3.23                    |
| FLOAT  | 0.10               | 0.40                    |
| INT    | 0.08               | 0.10                    |
