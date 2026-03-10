# Fast Walsh-Hadamard Transform — C Implementation

In-place FWHT for use in FDN reverb mixing matrix. Computes the exact same result as naive Hadamard matrix multiplication using only additions and subtractions — no multiplies, no trig, no lookup tables.

## Generic N (power of 2)

```c
void fwht(float *x, int n) {
    float a, b;
    for (int stride = 1; stride < n; stride <<= 1) {
        for (int i = 0; i < n; i += stride << 1) {
            for (int j = i; j < i + stride; j++) {
                a = x[j];
                b = x[j + stride];
                x[j]          = a + b;
                x[j + stride] = a - b;
            }
        }
    }
}
```

## Fixed N=8 (unrolled for execution without loops of loops in Daisy Seed)

```c
void fwht8(float *x) {
    float a, b;
    // Stage 1: stride 1
    for (int i = 0; i < 8; i += 2) {
        a = x[i]; b = x[i + 1];
        x[i] = a + b; x[i + 1] = a - b;
    }
    // Stage 2: stride 2
    for (int i = 0; i < 8; i += 4) {
        a = x[i];     b = x[i + 2];
        x[i]     = a + b; x[i + 2] = a - b;
        a = x[i + 1]; b = x[i + 3];
        x[i + 1] = a + b; x[i + 3] = a - b;
    }
    // Stage 3: stride 4
    for (int j = 0; j < 4; j++) {
        a = x[j]; b = x[j + 4];
        x[j]     = a + b; x[j + 4] = a - b;
    }
}
```

## Basic Nested Fast Walsh-Hadamard matrix (stride doubles each time)
```
// In-place FWHT for N=8
void fwht8(float *x) {
    float a, b;
    for (int stride = 1; stride < 8; stride <<= 1) {
        for (int i = 0; i < 8; i += stride << 1) {
            for (int j = i; j < i + stride; j++) {
                a = x[j];
                b = x[j + stride];
                x[j]          = a + b;
                x[j + stride] = a - b;
            }
        }
    }
}
```

## Complexity

| Method | Operations (N=8) | Operations (N=16) |
|--------|------------------|--------------------|
| Naive matmul | 64 multiply-adds | 256 multiply-adds |
| FWHT | 24 add/sub | 64 add/sub |

Normalize output by `1/sqrt(N)` to make the matrix unitary (energy-preserving). This scaling factor can be folded into the feedback gain coefficient to avoid extra multiplications per sample.
