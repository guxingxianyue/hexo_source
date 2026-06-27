---
title: Java读写锁和StampedLock：价格与库存快照缓存
date: 2025-05-22 10:00:00
tags: [Java, ReadWriteLock, StampedLock, 缓存, 供应链系统]
---

读写锁适合读多写少的场景。供应链系统里有大量这种数据：商品基础资料、供应商等级、仓库配置、价格策略、库存快照。读请求频繁，写请求相对较少。如果用普通互斥锁，读读之间也会互相阻塞，吞吐会被压低。

`ReentrantReadWriteLock` 的规则是：读读共享，读写互斥，写写互斥。`StampedLock` 在此基础上提供乐观读，适合对性能要求更高但代码复杂度可控的场景。

## 价格策略缓存

假设订单试算接口需要频繁读取供应商价格策略：

```java
public class PricePolicyCache {
    private final ReentrantReadWriteLock rwLock = new ReentrantReadWriteLock();
    private final Lock readLock = rwLock.readLock();
    private final Lock writeLock = rwLock.writeLock();

    private Map<Long, PricePolicy> policies = new HashMap<>();

    public PricePolicy get(long supplierId) {
        readLock.lock();
        try {
            return policies.get(supplierId);
        } finally {
            readLock.unlock();
        }
    }

    public void refresh(Map<Long, PricePolicy> latest) {
        writeLock.lock();
        try {
            policies = new HashMap<>(latest);
        } finally {
            writeLock.unlock();
        }
    }
}
```

多个订单试算线程可以同时读价格策略。刷新线程写入时，会阻塞读线程，确保读线程不会看到更新到一半的 Map。

## 不要在读锁里返回可变对象

上面的 `PricePolicy` 应该是不可变对象。如果返回的是可变对象，调用方可能绕过锁修改内部状态。

推荐：

```java
public final class PricePolicy {
    private final long supplierId;
    private final BigDecimal discountRate;
    private final List<PriceRule> rules;

    public PricePolicy(long supplierId, BigDecimal discountRate, List<PriceRule> rules) {
        this.supplierId = supplierId;
        this.discountRate = discountRate;
        this.rules = List.copyOf(rules);
    }
}
```

读写锁保护的是引用替换过程，不应该承担对象内部到处可变的复杂度。

## 锁降级

`ReentrantReadWriteLock` 支持锁降级：线程持有写锁时，再获取读锁，然后释放写锁。这样可以在刷新后继续以读锁身份使用新数据。

```java
public PricePolicy refreshAndGet(long supplierId) {
    writeLock.lock();
    try {
        policies = loadFromDatabase();
        readLock.lock();
    } finally {
        writeLock.unlock();
    }

    try {
        return policies.get(supplierId);
    } finally {
        readLock.unlock();
    }
}
```

不支持从读锁升级到写锁。读锁升级写锁很容易造成死锁，因为多个读线程都在等对方释放读锁。

## StampedLock 的乐观读

`StampedLock` 提供乐观读。乐观读不阻塞写，但读取后要验证期间是否发生写入。

库存快照缓存例子：

```java
public class InventorySnapshot {
    private final StampedLock lock = new StampedLock();

    private int availableQty;
    private int lockedQty;

    public int salableQty() {
        long stamp = lock.tryOptimisticRead();
        int available = availableQty;
        int locked = lockedQty;

        if (!lock.validate(stamp)) {
            stamp = lock.readLock();
            try {
                available = availableQty;
                locked = lockedQty;
            } finally {
                lock.unlockRead(stamp);
            }
        }
        return available - locked;
    }

    public void refresh(int available, int locked) {
        long stamp = lock.writeLock();
        try {
            this.availableQty = available;
            this.lockedQty = locked;
        } finally {
            lock.unlockWrite(stamp);
        }
    }
}
```

乐观读适合写入很少的场景。如果写入频繁，乐观读经常验证失败，反而增加复杂度。

## StampedLock 的注意点

`StampedLock` 不是可重入锁。同一线程重复获取写锁可能把自己卡住。它也不直接配合 `Condition`。因此它适合局部、简单、性能敏感的缓存或数值快照，不适合复杂业务流程锁。

供应链系统里，仓库维度的实时库存核心数据不应该只靠本地 `StampedLock` 控制。因为多实例部署下，每个 JVM 都有自己的锁。它适合保护本地缓存视图，最终一致性仍然依赖数据库和消息刷新。

## 小结

读写锁适合读多写少的本地共享数据。供应链系统里的价格策略、仓库配置、库存快照缓存都可以使用。选择上，普通读多写少用 `ReentrantReadWriteLock`；极高频读取、低频刷新、逻辑简单时可以评估 `StampedLock`。不管使用哪种锁，都要避免返回可变对象，并明确它只保护单 JVM 内存。

