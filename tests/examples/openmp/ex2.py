# coding: utf-8

# This example is the python implementation of ploop.1.f from OpenMP 4.5 examples

n = 100
n = int()

a = zeros(n, double)
b = zeros(n, double)

#$ omp parallel
#$ omp do
for i in range(1, n):
    b[i] = a[i] / 2.0 + a[i-1] / 2.0
#$ omp end do
#$ omp end parallel
