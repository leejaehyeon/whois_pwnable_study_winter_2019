oreo from [here](https://github.com/ctfs/write-ups-2014/tree/master/hack-lu-ctf-2014/oreo)

- house of spirit
- setting size & next size & alignment
- 유저가 free 에 넘기는 주소는 &chunk + 2 * SIZE_SZ 라는 거 잊지 말 것

- source 단에서 분석이 필요할 때 볼 거
1) ptmalloc2 source for malloc/free algorithm
2) glibc source for security checks
3) open the libc file on IDA pro so that we can see the real code & we can compare it with the assembly code
