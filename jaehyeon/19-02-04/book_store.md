<https://github.com/ctfs/write-ups-2015/tree/master/hack-lu-ctf-2015/exploiting/bookstore>

heap overflow + format string bug

후 포맷스트링 버그 너무 빡시다. 
- fini array 이용
- 디버깅 하는게 너무 빡셈. 넣으려는 target_address 가 계속 바뀌어서 포맷 스트링을 일반화해서 만들어야 함

- *** +- 연산자가 bitwise 연산자 보다 우선순위가 높다는 것을 기억하자
