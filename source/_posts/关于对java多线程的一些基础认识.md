title: 关于对java多线程的一些基础认识
date: 2016-03-05 20:47:08
tags: [技术文章]
---
## 一.线程的生命周期及五种基本状态
![五种基本状态](https://i.imgur.com/IE4s56r.jpg)

上图中基本上囊括了Java中多线程各重要知识点。掌握了上图中的各知识点，Java中的多线程也就基本上掌握了。主要包括：

#### Java线程具有五中基本状态

* 新建状态（New）：当线程对象对创建后，即进入了新建状态，如：Thread t = new MyThread();

* 就绪状态（Runnable）：当调用线程对象的start()方法（t.start();），线程即进入就绪状态。处于就绪状态的线程，只是说明此线程已经做好了准备，随时等待CPU调度执行，并不是说执行了t.start()此线程立即就会执行；

* 运行状态（Running）：当CPU开始调度处于就绪状态的线程时，此时线程才得以真正执行，即进入到运行状态。注：就     绪状态是进入到运行状态的唯一入口，也就是说，线程要想进入运行状态执行，首先必须处于就绪状态中；

* 阻塞状态（Blocked）：处于运行状态中的线程由于某种原因，暂时放弃对CPU的使用权，停止执行，此时进入阻塞状态，直到其进入到就绪状态，才 有机会再次被CPU调用以进入到运行状态。根据阻塞产生的原因不同，阻塞状态又可以分为三种：

	* 等待阻塞：运行状态中的线程执行wait()方法，使本线程进入到等待阻塞状态；

	* 同步阻塞 -- 线程在获取synchronized同步锁失败(因为锁被其它线程所占用)，它会进入同步阻塞状态；

	* 其他阻塞 -- 通过调用线程的sleep()或join()或发出了I/O请求时，线程会进入到阻塞状态。当sleep()状态超时、join()等待线程终止或者超时、或者I/O处理完毕时，线程重新转入就绪状态。

* 死亡状态（Dead）：线程执行完了或者因异常退出了run()方法，该线程结束生命周期。

## 二. Java多线程的创建及启动

###### Java中线程的创建常见有如三种基本形式

#### 1.继承Thread类，重写该类的run()方法。

	class MyThread extends Thread {
	    
	    private int i = 0;
	
	    @Override
	    public void run() {
	        for (i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	        }
	    }
	}

	public class ThreadTest {
	
	    public static void main(String[] args) {
	        for (int i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            if (i == 30) {
	                Thread myThread1 = new MyThread();     // 创建一个新的线程  myThread1  此线程进入新建状态
	                Thread myThread2 = new MyThread();     // 创建一个新的线程 myThread2 此线程进入新建状态
	                myThread1.start();                     // 调用start()方法使得线程进入就绪状态
	                myThread2.start();                     // 调用start()方法使得线程进入就绪状态
	            }
	        }
	    }
	}
	
如上所示，继承Thread类，通过重写run()方法定义了一个新的线程类MyThread，其中run()方法的方法体代表了线程需要完成的任务，称之为线程执行体。当创建此线程类对象时一个新的线程得以创建，并进入到线程新建状态。通过调用线程对象引用的start()方法，使得该线程进入到就绪状态，此时此线程并不一定会马上得以执行，这取决于CPU调度时机。

#### 2.实现Runnable接口，并重写该接口的run()方法，该run()方法同样是线程执行体，创建Runnable实现类的实例，并以此实例作为Thread类的target来创建Thread对象，该Thread对象才是真正的线程对象。

	class MyRunnable implements Runnable {
	    private int i = 0;
	
	    @Override
	    public void run() {
	        for (i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	        }
	    }
	}


	public class ThreadTest {
	
	    public static void main(String[] args) {
	        for (int i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            if (i == 30) {
	                Runnable myRunnable = new MyRunnable(); // 创建一个Runnable实现类的对象
	                Thread thread1 = new Thread(myRunnable); // 将myRunnable作为Thread target创建新的线程
	                Thread thread2 = new Thread(myRunnable);
	                thread1.start(); // 调用start()方法使得线程进入就绪状态
	                thread2.start();
	            }
	        }
	    }
	}

相信以上两种创建新线程的方式大家都很熟悉了，那么Thread和Runnable之间到底是什么关系呢？我们首先来看一下下面这个例子。

	public class ThreadTest {

	    public static void main(String[] args) {
	        for (int i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            if (i == 30) {
	                Runnable myRunnable = new MyRunnable();
	                Thread thread = new MyThread(myRunnable);
	                thread.start();
	            }
	        }
	    }
	}
	
	class MyRunnable implements Runnable {
	    private int i = 0;
	
	    @Override
	    public void run() {
	        System.out.println("in MyRunnable run");
	        for (i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	        }
	    }
	}
	
	class MyThread extends Thread {
	
	    private int i = 0;
	    
	    public MyThread(Runnable runnable){
	        super(runnable);
	    }
	
	    @Override
	    public void run() {
	        System.out.println("in MyThread run");
	        for (i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	        }
	    }
	}

同样的，与实现Runnable接口创建线程方式相似，不同的地方在于

	Thread thread = new MyThread(myRunnable);

那么这种方式可以顺利创建出一个新的线程么？答案是肯定的。至于此时的线程执行体到底是MyRunnable接口中的run()方法还是MyThread类中的run()方法呢？通过输出我们知道线程执行体是MyThread类中的run()方法。其实原因很简单，因为Thread类本身也是实现了Runnable接口，而run()方法最先是在Runnable接口中定义的方法。

	public interface Runnable {
	    
	    public abstract void run();
	     
	}	

我们看一下Thread类中对Runnable接口中run()方法的实现：

	@Override
    public void run() {
        if (target != null) {
            target.run();
        }
    }

也就是说，当执行到Thread类中的run()方法时，会首先判断target是否存在，存在则执行target中的run()方法，也就是实现了Runnable接口并重写了run()方法的类中的run()方法。但是上述给到的列子中，由于多态的存在，根本就没有执行到Thread类中的run()方法，而是直接先执行了运行时类型即MyThread类中的run()方法。

#### 3.使用Callable和Future接口创建线程。具体是创建Callable接口的实现类，并实现clall()方法。并使用FutureTask类来包装Callable实现类的对象，且以此FutureTask对象作为Thread对象的target来创建线程。
看着好像有点复杂，直接来看一个例子就清晰了。

	public class ThreadTest {
	
	    public static void main(String[] args) {
	
	        Callable<Integer> myCallable = new MyCallable();    // 创建MyCallable对象
	        FutureTask<Integer> ft = new FutureTask<Integer>(myCallable); //使用FutureTask来包装MyCallable对象
	
	        for (int i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            if (i == 30) {
	                Thread thread = new Thread(ft);   //FutureTask对象作为Thread对象的target创建新的线程
	                thread.start();                      //线程进入到就绪状态
	            }
	        }
	
	        System.out.println("主线程for循环执行完毕..");
	        
	        try {
	            int sum = ft.get();            //取得新创建的新线程中的call()方法返回的结果
	            System.out.println("sum = " + sum);
	        } catch (InterruptedException e) {
	            e.printStackTrace();
	        } catch (ExecutionException e) {
	            e.printStackTrace();
	        }
	
	    }
	}
	
	
	class MyCallable implements Callable<Integer> {
	    
		private int i = 0;
	
	    // 与run()方法不同的是，call()方法具有返回值
	    @Override
	    public Integer call() {
	        int sum = 0;
	        for (; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            sum += i;
	        }
	        return sum;
	    }
	
	}

首先，我们发现，在实现Callable接口中，此时不再是run()方法了，而是call()方法，此call()方法作为线程执行体，同时还具有返回值！在创建新的线程时，是通过FutureTask来包装MyCallable对象，同时作为了Thread对象的target。那么看下FutureTask类的定义：

	public class FutureTask<V> implements RunnableFuture<V> {
		//....
	}

	public interface RunnableFuture<V> extends Runnable, Future<V> {
		void run();
	}

于是，我们发现FutureTask类实际上是同时实现了Runnable和Future接口，由此才使得其具有Future和Runnable双重特性。通过Runnable特性，可以作为Thread对象的target，而Future特性，使得其可以取得新创建线程中的call()方法的返回值。

执行下此程序，我们发现sum = 4950永远都是最后输出的。而“主线程for循环执行完毕..”则很可能是在子线程循环中间输出。由CPU的线程调度机制，我们知道，“主线程for循环执行完毕..”的输出时机是没有任何问题的，那么为什么sum =4950会永远最后输出呢？

原因在于通过ft.get()方法获取子线程call()方法的返回值时，当子线程此方法还未执行完毕，ft.get()方法会一直阻塞，直到call()方法执行完毕才能取到返回值。

上述主要讲解了三种常见的线程创建方式，对于线程的启动而言，都是调用线程对象的start()方法，需要特别注意的是：
不能对同一线程对象两次调用start()方法。

## 三. Java多线程的就绪、运行和死亡状态
* 就绪状态转换为运行状态：当此线程得到处理器资源；

* 运行状态转换为就绪状态：当此线程主动调用yield()方法或在运行过程中失去处理器资源。

* 运行状态转换为死亡状态：当此线程线程执行体执行完毕或发生了异常。

此处需要特别注意的是：当调用线程的yield()方法时，线程从运行状态转换为就绪状态，但接下来CPU调度就绪状态中的哪个线程具有一定的随机性，因此，可能会出现A线程调用了yield()方法后，接下来CPU仍然调度了A线程的情况。

由于实际的业务需要，常常会遇到需要在特定时机终止某一线程的运行，使其进入到死亡状态。目前最通用的做法是设置一boolean型的变量，当条件满足时，使线程执行体快速执行完毕。如：

	public class ThreadTest {
	
	    public static void main(String[] args) {
	
	        MyRunnable myRunnable = new MyRunnable();
	        Thread thread = new Thread(myRunnable);
	        
	        for (int i = 0; i < 100; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	            if (i == 30) {
	                thread.start();
	            }
	            if(i == 40){
	                myRunnable.stopThread();
	            }
	        }
	    }
	}
	
	class MyRunnable implements Runnable {
	
	    private boolean stop;
	
	    @Override
	    public void run() {
	        for (int i = 0; i < 100 && !stop; i++) {
	            System.out.println(Thread.currentThread().getName() + " " + i);
	        }
	    }
	
	    public void stopThread() {
	        this.stop = true;
	    }
	
	}


