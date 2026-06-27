---
title: MySQL行锁与索引：库存预占为什么必须命中索引
date: 2025-04-03 09:40:00
tags: [MySQL, InnoDB, 行锁, 索引, 库存系统]
---

InnoDB 的行锁不是直接锁住“表里那一行数据”的抽象概念，而是锁住索引记录。这个细节决定了很多线上锁问题的根因：SQL 看起来只改一条业务数据，但因为没有命中合适索引，实际扫描和加锁范围远大于预期。

供应链系统里最容易踩坑的是库存预占。库存表通常按仓库、SKU、批次、库位维度管理，如果查询条件和索引设计不一致，一个订单扣库存可能阻塞另一批无关 SKU 的入库、移库或盘点。

## 库存表的索引设计

假设库存按仓库和 SKU 汇总：

```sql
CREATE TABLE scm_inventory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  warehouse_id BIGINT NOT NULL,
  sku_id BIGINT NOT NULL,
  available_qty INT NOT NULL,
  locked_qty INT NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_wh_sku (warehouse_id, sku_id),
  KEY idx_sku (sku_id)
) ENGINE=InnoDB;
```

订单预占库存时，最理想的 SQL 是：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - 5,
    locked_qty = locked_qty + 5,
    updated_at = NOW()
WHERE warehouse_id = 8
  AND sku_id = 1001
  AND available_qty >= 5;
```

这里能命中唯一索引 `uk_wh_sku`。InnoDB 可以快速定位到一条索引记录，然后对这条记录加排他锁。其他事务更新同仓不同 SKU，或者不同仓同 SKU，通常不会被它阻塞。

## 没有命中索引会发生什么

如果业务代码写成这样：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - 5,
    locked_qty = locked_qty + 5
WHERE sku_id = 1001
  AND available_qty >= 5;
```

这条 SQL 少了 `warehouse_id`。如果只命中 `idx_sku`，它可能扫描所有仓库里 SKU 1001 的库存记录。对于全国仓、多渠道库存系统，这个范围可能很大。

更差的是用函数或隐式转换破坏索引：

```sql
SELECT *
FROM scm_inventory
WHERE CAST(sku_id AS CHAR) = '1001'
FOR UPDATE;
```

当索引失效时，数据库需要扫描更多记录。扫描过程中，当前读和更新语句可能对更多索引记录加锁，导致锁等待范围扩大。线上表现通常是：明明两个订单不是同一个仓库，却互相等待。

## 用 EXPLAIN 验证锁范围的前提

锁问题先看 SQL 是否按预期走索引：

```sql
EXPLAIN
UPDATE scm_inventory
SET available_qty = available_qty - 5,
    locked_qty = locked_qty + 5
WHERE warehouse_id = 8
  AND sku_id = 1001
  AND available_qty >= 5;
```

重点看：

- `key` 是否是预期索引。
- `type` 是否是 `const`、`ref` 或 `range`。
- `rows` 是否接近业务预期。

如果 `rows` 远大于 1，就要警惕锁范围已经被放大。

## Java 侧的正确调用方式

库存预占接口不要先查库存再在 Java 里判断。推荐直接执行条件更新：

```java
@Transactional
public void reserveStock(long warehouseId, long skuId, int qty) {
    int affected = inventoryMapper.reserve(warehouseId, skuId, qty);
    if (affected != 1) {
        throw new BizException("库存不足，无法预占");
    }
    inventoryLogMapper.insertReserveLog(warehouseId, skuId, qty);
}
```

对应 Mapper SQL：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - #{qty},
    locked_qty = locked_qty + #{qty},
    updated_at = NOW()
WHERE warehouse_id = #{warehouseId}
  AND sku_id = #{skuId}
  AND available_qty >= #{qty}
```

这个写法有两个优点。第一，库存判断和扣减是一个原子更新。第二，锁范围由唯一索引控制，容易解释和排查。

## 批量库存预占的加锁顺序

一个订单可能包含多个 SKU。批量扣减时，如果两个事务以不同顺序锁 SKU，就容易死锁。

事务 A：

```text
先锁 SKU 1001
再锁 SKU 1002
```

事务 B：

```text
先锁 SKU 1002
再锁 SKU 1001
```

两个事务互相等待，就会死锁。解决办法是固定加锁顺序，比如按 `sku_id` 升序处理：

```java
items.stream()
     .sorted(Comparator.comparing(OrderItem::getSkuId))
     .forEach(item -> reserveStock(order.getWarehouseId(), item.getSkuId(), item.getQty()));
```

数据库仍然可能检测到死锁并回滚其中一个事务，所以业务层还要对死锁异常做有限重试。但固定顺序能显著降低死锁概率。

## 索引设计原则

库存锁相关 SQL 的索引设计应该从业务唯一性出发。

如果库存粒度是仓库 + SKU：

```sql
UNIQUE KEY uk_wh_sku (warehouse_id, sku_id)
```

如果库存粒度是仓库 + SKU + 批次 + 库位：

```sql
UNIQUE KEY uk_wh_sku_batch_bin (warehouse_id, sku_id, batch_no, bin_code)
```

业务 SQL 必须尽量带齐唯一维度。缺一个维度，锁范围和业务语义都会变模糊。

## 小结

InnoDB 行锁的关键是索引。供应链系统里，库存、批次、库位、单据明细这些表的数据量大、并发高，锁范围稍微变大就会影响吞吐。写库存类 SQL 时，必须用业务唯一索引定位记录，用条件更新完成判断和修改，并在批量处理时固定加锁顺序。

