// SPDX-FileCopyrightText: 2026 Jimmy Miller
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#include <stdio.h>
#include <stdint.h>
int64_t sum(int64_t, int64_t), callmany(int64_t, int64_t), pressure(int64_t, int64_t), swapper(int64_t, int64_t, int64_t, int64_t);
int64_t manyargs(int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t,int64_t), callmanyargs(int64_t);
static int64_t pressure_ref(int64_t a, int64_t b) {
  int64_t v[33], w[32]; v[1]=a+b; v[2]=v[1]+a; v[3]=v[2]+b;
  for (int i=4;i<=32;i++) v[i]=v[i-1]+v[i-3];
  w[1]=v[1]+v[32]; for(int i=2;i<=31;i++) w[i]=w[i-1]+v[i]; return w[31];
}
int main(void) {
  int bad = 0;
  #define CHECK(e, want) do { int64_t got = (e); if (got != (want)) { printf("FAIL %s = %lld want %lld\n", #e, (long long)got, (long long)(want)); bad = 1; } } while (0)
  CHECK(sum(10, 1), 55); CHECK(sum(0, 1), 0); CHECK(sum(1000, 1), 500500);
  CHECK(callmany(3, 4), 11);
  CHECK(pressure(1, 2), pressure_ref(1, 2)); CHECK(pressure(-7, 3), pressure_ref(-7, 3));
  CHECK(swapper(5, 9, 0, 1), -4); CHECK(swapper(5, 9, 1, 1), 4); CHECK(swapper(5, 9, 6, 1), -4); CHECK(swapper(5, 9, 7, 1), 4);
  CHECK(manyargs(1,2,3,4,5,6,7,8,9,10,11), 1-2+3-4+5-6+7-8+9-10+11);
  CHECK(callmanyargs(5), manyargs(5,5,5,5,5,5,5,5,5,5,5) ? manyargs(manyargs(5,5,5,5,5,5,5,5,5,5,5),5,manyargs(5,5,5,5,5,5,5,5,5,5,5),5,manyargs(5,5,5,5,5,5,5,5,5,5,5),5,manyargs(5,5,5,5,5,5,5,5,5,5,5),5,manyargs(5,5,5,5,5,5,5,5,5,5,5),5,manyargs(5,5,5,5,5,5,5,5,5,5,5)) : 0);
  if (!bad) printf("ok\n");
  return bad;
}
