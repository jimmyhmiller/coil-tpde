#include <stdio.h>
#include <stdint.h>
int64_t sum_to(int64_t), fib(int64_t), count_down(int64_t, int64_t), mem(int64_t *, int64_t);
double fpoly(double);
int64_t mulhi_signed(int64_t, int64_t), classify(int64_t);
int main(void) {
  int bad = 0;
#define CHECK(e, want) do { int64_t got = (e); if (got != (int64_t)(want)) { printf("FAIL %s = %lld want %lld\n", #e, (long long)got, (long long)(want)); bad = 1; } } while (0)
  CHECK(sum_to(10), 285); CHECK(sum_to(0), 0);
  CHECK(fib(20), 6765);
  CHECK(count_down(100000000, 0), 5000000050000000LL);
  int64_t arr[8] = {3, 1, 4, 1, 5, 9, 2, 6};
  CHECK(mem(arr, 2), 9);
  CHECK(arr[0], 3);
  double fp = fpoly(3.0); if (fp != 3.0 * 3.0 * 0.5 + 1.25) { printf("FAIL fpoly %f\n", fp); bad = 1; }
  CHECK(mulhi_signed(0x123456789LL, 0x7FFFFFFFFFFFLL), (int64_t)(((__int128)0x123456789LL * 0x7FFFFFFFFFFFLL) >> 64));
  CHECK(mulhi_signed(-5, 7), -1);
  CHECK(classify(1), 10); CHECK(classify(2), 20); CHECK(classify(7), 70); CHECK(classify(3), -1); CHECK(classify(-9), -1);
  if (!bad) printf("ok\n");
  return bad;
}
