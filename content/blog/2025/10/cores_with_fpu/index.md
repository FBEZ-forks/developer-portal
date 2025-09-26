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

## Introduction

While reading datasheets, forums or even announcement, you have surely glanced at core descriptions and stumbled across several acronyms. One of them is FPU, which stands for floating point unit. As the name implies, it is used to perform floating point calculation. But what does this exactly mean? Can't cores without FPU do such calculations? 

Sure they do. So what's the point? Well, speed. 

In this article we will explore first what a `float` actually is, how does an FPU make the calculation faster and which Espressif cores have an FPU. In the end we use a simple benchmark to show how faster the calculation can be, so you can evaluate when you need a core with FPU and when not. 

## What is a float

When you store an **integer** in memory, each bit directly represents the number’s value. For a 32-bit signed integer, the highest bit indicates the sign, and the remaining bits represent the magnitude using two’s complement. For example, `5` is stored as:

```
00000000 00000000 00000000 00000101
```

and `–5` as:

```
11111111 11111111 11111111 11111011
```

A **float**, in contrast, divides its bits into three conceptual parts: a **sign**, a **scale** to indicate magnitude, and the **precision digits** of the value. This allows a single 32-bit float to represent both very large and very small numbers, but with less precision than integers.


### The IEEE 754 standard

To make floating-point behavior consistent across platforms, the **IEEE 754 standard** defines exactly how floats are stored in memory. Single precision (`float`) uses 32 bits, split into a sign, an exponent (scale), and a mantissa (precision), while double precision (`double`) uses 64 bits with a larger exponent and mantissa.

For example, the number `5.0` as a 32-bit float is represented as:

```
01000000 01000000 00000000 00000000
```

Breaking it down:

* **Sign bit (0)** &rarr; positive
* **Exponent (10000001)** &rarr; encodes 2²
* **Mantissa (01000000000000000000000)** &rarr; encodes 1.25

Using the IEEE 754 formula:

**(–1)^sign × 1.mantissa × 2^(exponent–bias) = 5.0**

This standard ensures consistency for floating-point math, whether calculations are performed in hardware with an FPU or in software via emulation routines.

### Performing float calculations

On a CPU with an FPU, operations like addition, multiplication, or square root execute directly in hardware using specialized instructions, making them fast and simple.

On a CPU **without an FPU**, like the ESP32-C3, there are no native float instructions. To perform a floating-point operation, you must emulate it using **integer arithmetic**, carefully handling the sign, exponent, and mantissa according to the IEEE 754 standard. For example, adding two floats `a` and `b` in software involves steps like:

1. Extract the sign, exponent, and mantissa from each number.
2. Align the exponents by shifting the mantissa of the smaller number.
3. Add or subtract the mantissas depending on the signs.
4. Normalize the result and adjust the exponent if necessary.
5. Pack the sign, exponent, and mantissa back into a 32-bit word.

A highly simplified illustration in C-like pseudocode:

```c
uint32_t float_add(uint32_t a, uint32_t b) {
    int sign_a = a >> 31;
    int sign_b = b >> 31;
    int exp_a  = (a >> 23) & 0xFF;
    int exp_b  = (b >> 23) & 0xFF;
    uint32_t man_a = (a & 0x7FFFFF) | 0x800000; // implicit 1
    uint32_t man_b = (b & 0x7FFFFF) | 0x800000;

    // align exponents
    if (exp_a > exp_b) man_b >>= (exp_a - exp_b);
    else              man_a >>= (exp_b - exp_a);

    // add mantissas
    uint32_t man_r = (sign_a == sign_b) ? man_a + man_b : man_a - man_b;

    // normalize result (simplified)
    int exp_r = (exp_a > exp_b) ? exp_a : exp_b;
    while ((man_r & 0x800000) == 0) { man_r <<= 1; exp_r--; }

    return (sign_a << 31) | ((exp_r & 0xFF) << 23) | (man_r & 0x7FFFFF);
}
```

Even this simplified version is already **much more work than a single FPU instruction**, and handling all edge cases (overflow, underflow, NaNs, infinities, rounding) adds significant complexity.

This example illustrates why standard libraries provide dedicated routines for floating-point arithmetic. Libraries such as libc on Linux or musl include tested implementations of both low-level float operations and higher-level math functions, so developers don’t have to implement them manually. On the ESP32-C3, Espressif relies on newlibc, a C standard library optimized for embedded systems, to provide these routines. On CPUs without an FPU, newlibc handles the complex integer-based emulation of IEEE 754 operations, ensuring correct results while simplifying development.

### newlibc

On embedded RISC-V systems like the ESP32-C3, **newlibc** provides the standard C library support for floating-point operations. It is structured in two layers:

At the low level, **libgcc** implements the primitive IEEE 754 operations in software. These routines emulate a hardware FPU using integer instructions and handle all the edge cases of floating-point arithmetic, including rounding, overflow, underflow, infinities, and NaNs. Typical routines include:

* **Arithmetic:** `__addsf3`, `__subsf3`, `__mulsf3`, `__divsf3` (single-precision), and `__adddf3`, `__muldf3` (double-precision).
* **Negation and absolute value:** `__negsf2`, `__abssf2`.
* **Comparisons:** `__eqsf2`, `__ltsf2`, `__gesf2`, etc.
* **Conversions:** between integers and floats or doubles, e.g., `__floatsisf`, `__fixsfsi`, `__fixunsdfsi`.

These helpers form the foundation for all floating-point operations on a CPU without an FPU, allowing higher-level routines to rely on them for correctness.

At a higher level, **libm** provides the familiar `<math.h>` functions, such as `sinf`, `cosf`, `sqrtf`, `expf`, and `logf`. These functions rely on the low-level helpers to perform their calculations correctly. For example, computing `sqrtf(2.0f)` on the ESP32-C3 is a software routine that uses iterative methods (like Newton–Raphson) together with integer arithmetic on the mantissa and exponent.

{{< alert icon="lightbulb" iconColor="#179299"  cardColor="#9cccce">}}
Functions in newlib like `sinf`, `cosf`, and `sqrtf` operate on single-precision floats (`float`), while the versions without the `f` suffix operate on doubles. 
{{< /alert >}}


With an FPU, these operations can be executed directly as hardware instructions, making them fast and efficient. Without an FPU, newlibc ensures that all floating-point operations and math functions behave correctly according to IEEE 754, freeing developers from having to implement complex routines themselves.


## What is an FPU

A **Floating Point Unit (FPU)** is a specialized part of a processor designed to handle **floating-point arithmetic directly in hardware**. While any CPU can perform floating-point calculations using software routines—like the ones implemented in newlibc on the ESP32-C3—an FPU executes these operations **much faster** by providing dedicated instructions for addition, subtraction, multiplication, division, and sometimes more advanced functions such as square roots or trigonometry.

The main advantage of an FPU is **speed**. Floating-point arithmetic in software requires multiple integer operations to manipulate the sign, exponent, and mantissa of a number, whereas an FPU can produce the same result in a single instruction. This difference becomes especially significant in applications that involve **lots of numerical computation**, such as digital signal processing, machine learning, or 3D graphics.

#### Single vs. Double Precision

Floating-point numbers come in different levels of precision, which FPUs can handle:

* **Single Precision (32-bit float):**
  Uses 1 bit for the sign, 8 bits for the exponent, and 23 bits for the mantissa. It provides about **7 decimal digits of precision** and is commonly used in embedded applications due to its lower memory footprint and faster computation.

* **Double Precision (64-bit float):**
  Uses 1 bit for the sign, 11 bits for the exponent, and 52 bits for the mantissa. It offers about **15–16 decimal digits of precision** but requires more memory and cycles to compute. Double precision is useful when high numerical accuracy is critical, such as in scientific calculations or precise control systems.

By including an FPU, a processor can execute both single and double-precision operations natively, delivering a **dramatic performance boost** over software-emulated arithmetic. For cores without an FPU, like the ESP32-C3, libraries like newlibc emulate these operations in software, ensuring correctness but at a significant speed cost.

With a clear understanding of what an FPU does and why it matters, the next step is to see which Espressif cores actually include hardware FPUs and what types of floating-point precision they support.

### Which cores have an FPU

Since an FPU is not strictly required for a processor to function, not all Espressif cores include one. If you want a quick overview, Espressif provides a concise [SoC Product Portfolio](https://products.espressif.com/static/Espressif%20SoC%20Product%20Portfolio.pdf) that highlights the key features of each chip, including whether an FPU is present.

In practice, FPUs are found in the cores designed for higher computational workloads, where fast floating-point arithmetic makes a tangible difference. These include the **ESP32, ESP32-S3, ESP32-H4, and ESP32-P4**.

All of these cores feature a **single-precision FPU**, which is sufficient for typical embedded applications, digital signal processing, and lightweight machine learning tasks. 


| Core      | FPU |
| --------- | --- |
| ESP32     | X   |
| ESP32-S2  |     |
| ESP32-S3  | X   |
| ESP32-C2  |     |
| ESP32-C3  |     |
| ESP32-C5  |     |
| ESP32-C6  |     |
| ESP32-C61 |     |
| ESP32-H2  |     |
| ESP32-H4  | X   |
| ESP32-P4  | X   |


To put the impact of an FPU into perspective, the following benchmark compares the execution of the same floating-point workload on two Espressif cores—one with a hardware FPU and one without—highlighting the dramatic difference in speed and efficiency.

### Benchmark

To measure the performance improvement, we will measure the average cycle number required by a core with FPU and one without FPU to do the following functions
* `float_sum10`, `double_sum10`: adding 10 to given number
* `float_div10`, `double_div10`: dividing the number by 10
* `cosf`, `cos`: performing the cosine of the number 
* `float_mixed`, `double_mixed`: performing a complex calculation with division and trigonometry `cos(sqrtf(value / 2.3 * 0.5 / value))`

Each function is performed 10000 times in a loop and the total number of cycles is divided by 10000. 

<details>
<summary>Full benchmark code </summary>

```c
#include <stdio.h>
#include <inttypes.h>
#include <stdio.h>
#include <math.h>

#include <esp_cpu.h>
#include <esp_system.h>
#include <esp_chip_info.h>
#include <esp_random.h>
#include <esp_log.h>

#define TAG         "test"
#define ITERATIONS  10000

static void float_test(const char* label, float seed, float (*function) (float))
{
    uint32_t start_cycles = esp_cpu_get_cycle_count();
    for (uint32_t i = 0; i < ITERATIONS; i++)
    {
        seed = function(seed);
    }
    uint32_t end_cycles = esp_cpu_get_cycle_count();

    printf(TAG ": %s %-10.10s average %"PRIu32 " cycles\n",label,  "float:", (end_cycles - start_cycles) / ITERATIONS);
}

static void double_test(const char* label, double seed, double (*function) (double))
{
    uint32_t start_cycles = esp_cpu_get_cycle_count();
    for (uint32_t i = 0; i < ITERATIONS; i++)
    {
        seed = function(seed);
    }
    uint32_t end_cycles = esp_cpu_get_cycle_count();

    printf(TAG ": %s %-10.10s average %"PRIu32 " cycles\n", label, "double:", (end_cycles - start_cycles) / ITERATIONS);
}

typedef struct {
    float (*float_function) (float);
    double (*double_function) (double);
} test_t;

static void test(const char* label, test_t* test) {
    printf(TAG ": %s\n", label);

    double seed = 123456.789;

    if (test->float_function != NULL) {
        float_test(label, (float) seed, test->float_function);
    }

    if (test->double_function != NULL) {
        double_test(label, (double) seed, test->double_function);
    }

    printf("\n");
}

/*** trivial functions ***/
static float float_sum10(float value) {
    return (value + 10);
}

static double double_sum10(double value) {
    return (value + 10);
}

static float float_div10(float value) {
    return (value / 10);
}

static double double_div10(double value) {
    return (value / 10);
}

/*
 * mixed calculations
 */
static float float_mixed(float value) {
    return cosf(sqrtf(value / 2.3f * 0.5f / value));
}

static double double_mixed(double value) {
    return cos(sqrt(value / 2.3 * 0.5 / value));
}

void app_main(void)
{
    esp_chip_info_t chip_info;
    esp_chip_info(&chip_info);

    const char *model;
    switch (chip_info.model) {
        case CHIP_ESP32:
            model = "ESP32";
            break;
        case CHIP_ESP32S2:
            model = "ESP32-S2";
            break;
        case CHIP_ESP32S3:
            model = "ESP32-S3";
            break;
        case CHIP_ESP32C3:
            model = "ESP32-C3";
            break;
        case CHIP_ESP32H2:
            model = "ESP32-H2";
            break;
        case CHIP_ESP32C2:
            model = "ESP32-C2";
            break;
        case CHIP_ESP32C6:
            model = "ESP32-C6";
            break;
        default:
            model = "<UNKNOWN>";
            break;
    }
    printf("\n");
    printf(TAG ": CHIP: %s\n", model);
    printf("\n");

    test_t sum10 = {
        .float_function =   float_sum10,
        .double_function =  double_sum10,
    };
    test("SUM", &sum10);

    test_t div10 = {
        .float_function =   float_div10,
        .double_function =  double_div10,
    };
    test("DIV", &div10);

    test_t cosine = {
        .float_function =   cosf,
        .double_function =  cos,
    };
    test("COS", &cosine);

    test_t mixed = {
        .float_function =   float_mixed,
        .double_function =  double_mixed,
    };
    test("MIX", &mixed);
}
```

</details>

The results are collected in the following table. 

|          |      SUM      |            |      DIV      |            |      COS      |            |      MIX      |            |
|----------|---------------|------------|---------------|------------|---------------|------------|---------------|------------|
|          | float         | double     | float         | double     | float         | double     | float         | double     |
| ESP32C3  | 100           | 122        | 102           | 133        | 2377          | 3560       | 3659          | 6074       |
| ESP32S3  | 25            | 70         | 69            | 75         | 121           | 1619       | 312           | 3886       |
| Delta cycles | -75       | -52        | -33           | -58        | -2256         | -1941      | -3347         | -2188      |
| Saving   | 75%           | 43%        | 32%           | 44%        | 95%           | 55%        | 91%           | 36%        |


As expected, single precision float calculation show the biggest saving in machine cycles, with a peak of 95% reached with the cosine function.
This means that if your application requires intense vector math, an FPU can come quite handy. 

## Conclusion

In this article, we explored floating-point numbers, how CPUs perform these calculations with and without an FPU, and which Espressif cores include one. Benchmarks showed that cores with an FPU executed operations, especially single-precision, much faster, demonstrating the clear performance advantage of hardware FPUs for computation heavy applications.


<!-- 

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


