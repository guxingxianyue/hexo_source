---
title: Redis入门：数据结构、缓存和供应链业务场景
date: 2017-05-10 21:13:08
tags: [Redis, 缓存, 数据结构, 供应链系统]
---

Redis 是高性能内存数据存储，常用于缓存、分布式锁、计数器、排行榜、队列和限流。学习 Redis 不应该停留在安装命令，而要理解它的数据结构适合解决什么业务问题，以及缓存一致性、击穿、穿透、雪崩这些生产风险。

## 整体流程

![Redis 数据结构和供应链场景](/images/tech-flowcharts/redis-data-structure-flow.svg)

## Redis 适合做什么

Redis 的核心优势是低延迟和丰富的数据结构。常用结构包括：

1. String：缓存单个值、计数器、分布式锁 value。
2. Hash：缓存对象字段，例如 SKU 基础信息。
3. List：简单队列，但复杂消息场景更推荐消息队列。
4. Set：去重集合，例如活动参与用户。
5. ZSet：带分数排序，例如热销商品排行。
6. Stream：Redis 5 引入的消息流，适合轻量事件流。

供应链系统里，Redis 常见用途是缓存库存展示值、仓库路由规则、承运商配置、SKU 基础资料，以及做接口限流和幂等控制。

## 缓存 SKU 信息

SKU 基础资料读多写少，适合缓存：

```java
public SkuInfo getSkuInfo(String skuCode) {
    String key = "sku:info:" + skuCode;
    SkuInfo cached = redisTemplate.opsForValue().get(key);
    if (cached != null) {
        return cached;
    }

    SkuInfo skuInfo = skuRepository.findByCode(skuCode);
    if (skuInfo == null) {
        redisTemplate.opsForValue().set(key, SkuInfo.empty(), Duration.ofMinutes(5));
        return null;
    }

    redisTemplate.opsForValue().set(key, skuInfo, Duration.ofHours(6));
    return skuInfo;
}
```

这里要注意两点：

1. 空值也可以短时间缓存，防止缓存穿透。
2. 缓存必须设置过期时间，避免长期脏数据。

## 缓存库存要谨慎

库存是强一致性敏感数据。展示库存可以缓存，但下单扣减不能只依赖 Redis 缓存值。

更稳妥的做法是：

```text
下单预占 -> 数据库条件更新保证一致性
库存展示 -> Redis 缓存提升查询性能
库存变更 -> 发布事件刷新或删除缓存
```

示例：

```java
public void refreshInventoryCache(long warehouseId, long skuId) {
    InventoryRecord record = inventoryRepository.find(warehouseId, skuId);
    String key = "inventory:view:" + warehouseId + ":" + skuId;
    redisTemplate.opsForValue().set(key, record.toView(), Duration.ofMinutes(10));
}
```

缓存可以提升读性能，但数据库仍然是库存一致性的最终来源。

## 分布式锁基本原则

Redis 可以实现分布式锁，但要满足几个条件：

```java
Boolean ok = redisTemplate.opsForValue().setIfAbsent(
        "lock:order:" + orderNo,
        requestId,
        Duration.ofSeconds(10)
);
```

释放锁时必须校验 value，避免删除别人的锁。生产环境建议使用成熟客户端，例如 Redisson，并结合业务幂等设计，而不是只依赖锁。

## 缓存风险

缓存穿透：请求不存在的数据，绕过缓存打到数据库。处理方式是参数校验、空值缓存、布隆过滤器。

缓存击穿：热点 key 过期，大量请求同时访问数据库。处理方式是互斥重建、逻辑过期、热点 key 不短过期。

缓存雪崩：大量 key 同时过期。处理方式是过期时间加随机值、分批预热、多级缓存。

缓存脏读：数据库已变更，缓存未刷新。处理方式是先更新数据库，再删除缓存，必要时通过消息进行二次删除或异步刷新。

## 小结

Redis 入门要围绕数据结构和业务场景学习。供应链系统里，缓存能显著提升 SKU、仓库、路由、库存展示等读性能，但订单扣减、库存预占、财务结算这类核心一致性流程不能只依赖缓存。Redis 是加速器，不应该成为一致性的唯一防线。
