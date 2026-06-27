---
title: Java synchronized与Monitor：仓库作业状态机的互斥控制
date: 2025-04-24 10:00:00
tags: [Java, synchronized, Monitor, 并发编程, 仓储系统]
---

`synchronized` 是 Java 最基础的互斥机制。它的语义直接：进入同步代码前获取对象监视器，退出时释放监视器。对供应链系统来说，它适合保护 JVM 内部的小范围共享状态，比如本地缓存、状态机对象、批处理任务上下文。

需要先明确边界：`synchronized` 只在当前 JVM 内有效。如果系统部署了多个实例，它不能保护数据库里的订单或库存。跨实例一致性仍然要依赖数据库锁、唯一约束、分布式锁或消息幂等。

## 仓库作业状态机例子

仓库作业单可能有这些状态：

```text
CREATED -> PICKING -> PACKED -> SHIPPED
```

如果状态机对象在内存里被多个线程访问，就要保证状态转换互斥：

```java
public class WarehouseTaskStateMachine {
    private String status = "CREATED";

    public synchronized void startPicking() {
        if (!"CREATED".equals(status)) {
            throw new IllegalStateException("只有已创建任务才能开始拣货");
        }
        status = "PICKING";
    }

    public synchronized void pack() {
        if (!"PICKING".equals(status)) {
            throw new IllegalStateException("只有拣货中任务才能打包");
        }
        status = "PACKED";
    }

    public synchronized String currentStatus() {
        return status;
    }
}
```

这里锁对象是 `this`。同一个状态机实例的三个同步方法互斥，避免一个线程正在从 `CREATED` 改为 `PICKING` 时，另一个线程同时执行 `pack()`。

## synchronized 锁住的到底是谁

实例方法：

```java
public synchronized void method() {}
```

等价于：

```java
public void method() {
    synchronized (this) {
        // ...
    }
}
```

静态方法锁住的是 Class 对象：

```java
public static synchronized void reloadGlobalConfig() {}
```

等价于：

```java
synchronized (ConfigCenter.class) {
    // ...
}
```

代码块可以指定任意锁对象：

```java
private final Object lock = new Object();

public void changeStatus() {
    synchronized (lock) {
        // 修改共享状态
    }
}
```

工程上更推荐使用私有 final 锁对象，避免外部代码拿到 `this` 后参与锁竞争。

## 可重入性

`synchronized` 是可重入锁。同一个线程已经持有某对象锁时，可以再次进入同一把锁保护的代码。

```java
public synchronized void finishPicking() {
    validatePicking();
    status = "PACKED";
}

private synchronized void validatePicking() {
    if (!"PICKING".equals(status)) {
        throw new IllegalStateException("状态错误");
    }
}
```

`finishPicking()` 调用 `validatePicking()` 不会死锁，因为持锁线程可以重入。可重入性让同步方法之间的组合更自然，但也要避免同步方法调用链过深，导致锁持有时间不可控。

## wait 和 notify 的条件协作

如果仓库打包线程要等拣货完成，可以使用 `wait/notify`，但要严格放在同步块里，并用 while 判断条件：

```java
public class PackingGate {
    private boolean pickingFinished = false;

    public synchronized void finishPicking() {
        pickingFinished = true;
        notifyAll();
    }

    public synchronized void waitForPicking() throws InterruptedException {
        while (!pickingFinished) {
            wait();
        }
    }
}
```

使用 `while` 而不是 `if`，是为了防止虚假唤醒或被唤醒后条件已经被其他线程改变。实际项目中，如果等待条件复杂，更建议使用 `BlockingQueue`、`CountDownLatch`、`Condition` 等工具。

## 不要锁住慢操作

下面是错误示例：

```java
public synchronized void ship(long taskId) {
    updateLocalStatus(taskId, "SHIPPING");
    wmsClient.notifyShipment(taskId);
    updateLocalStatus(taskId, "SHIPPED");
}
```

远程调用 `wmsClient.notifyShipment` 可能耗时几百毫秒甚至超时。它在同步方法里执行，会导致其他线程长时间无法进入同一对象的同步方法。

更合理的做法是缩小锁范围：

```java
public void ship(long taskId) {
    synchronized (lock) {
        updateLocalStatus(taskId, "SHIPPING");
    }

    wmsClient.notifyShipment(taskId);

    synchronized (lock) {
        updateLocalStatus(taskId, "SHIPPED");
    }
}
```

如果本地状态必须和远程调用严格一致，就不应该靠一个 JVM 锁解决，而应该用数据库状态机、消息表和补偿任务。

## 和数据库锁的边界

如果状态存在数据库里，Java 本地锁不能防止另一个应用实例修改同一记录。供应链系统通常是多实例部署，所以最终状态变更应落到数据库条件更新：

```sql
UPDATE scm_warehouse_task
SET status = 'PICKING'
WHERE id = #{taskId}
  AND status = 'CREATED';
```

Java 的 `synchronized` 只适合保护当前实例内的辅助状态，比如本地缓存、批处理内存队列、状态机对象。核心业务一致性必须由数据库约束兜底。

## 小结

`synchronized` 的优点是简单、语义清晰、异常退出自动释放锁。它适合小范围、短时间、单 JVM 内的互斥。供应链系统使用它时，必须控制锁对象、缩小锁范围、避免锁住远程调用，并明确它不能替代数据库并发控制。

