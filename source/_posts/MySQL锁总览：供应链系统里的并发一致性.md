---
title: MySQL锁总览：供应链系统里的并发一致性
date: 2025-03-06 09:30:00
tags: [MySQL, InnoDB, 锁, 事务, 供应链系统]
---

供应链系统里的并发问题通常不是抽象的“线程安全”，而是非常具体的业务错误：库存被扣成负数、同一张采购单被重复审核、同一个批次被两个上架任务同时占用、同一笔应付单被重复生成。MySQL 锁的价值就在这里，它让多个事务在修改同一批业务数据时有确定的顺序。

理解 MySQL 锁，不能只背表锁、行锁、共享锁、排他锁这些名词。更重要的是搞清楚四个问题：锁的对象是什么，锁什么时候加上，锁什么时候释放，不同锁之间是否兼容。

## MySQL 锁设计流程

![MySQL 锁设计流程](/images/tech-flowcharts/mysql-lock-overview-supply-flow.svg)

## 供应链里的典型并发场景

假设有一张库存表：

```sql
CREATE TABLE scm_inventory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  warehouse_id BIGINT NOT NULL,
  sku_id BIGINT NOT NULL,
  available_qty INT NOT NULL,
  locked_qty INT NOT NULL,
  version INT NOT NULL DEFAULT 0,
  UNIQUE KEY uk_wh_sku (warehouse_id, sku_id)
) ENGINE=InnoDB;
```

两个订单同时预占同一个仓库的同一个 SKU。每个订单都要锁定 8 件库存，当前可用库存只有 10。如果两个事务都先读到 `available_qty = 10`，然后各自扣减，就会超卖。

错误写法通常是先查再改：

```sql
SELECT available_qty
FROM scm_inventory
WHERE warehouse_id = 1 AND sku_id = 1001;

UPDATE scm_inventory
SET available_qty = available_qty - 8,
    locked_qty = locked_qty + 8
WHERE warehouse_id = 1 AND sku_id = 1001;
```

这两条 SQL 分开执行时，如果没有事务和锁保护，中间状态会被其他事务插入。更稳的做法是让条件判断和扣减在一条更新语句里完成：

```sql
UPDATE scm_inventory
SET available_qty = available_qty - 8,
    locked_qty = locked_qty + 8,
    version = version + 1
WHERE warehouse_id = 1
  AND sku_id = 1001
  AND available_qty >= 8;
```

如果返回影响行数是 1，说明预占成功；如果是 0，说明库存不足或记录不存在。这个写法利用了 InnoDB 对更新记录加排他锁的能力，也避免了应用层先读后写的竞态。

## 表锁、行锁和意向锁

表锁锁住整张表。粒度大，管理简单，但并发能力差。供应链系统里订单、库存、出入库单都是高频表，业务代码一般不应该主动加表锁。

行锁锁住索引记录。InnoDB 的核心并发能力来自行锁。两个事务修改不同 SKU 的库存时，只要走的是不同索引记录，就可以并发执行。

意向锁是 InnoDB 自动加在表级别的锁，用来表示“这个事务准备在表里的某些行上加锁”。它主要用于协调表锁和行锁。业务开发不需要手动控制意向锁，但排查锁等待时要能看懂 `IS`、`IX`。

## 共享锁和排他锁

共享锁用于读，多个事务可以同时持有共享锁。排他锁用于写，一个事务持有排他锁时，其他事务不能再对同一记录加共享锁或排他锁。

在供应链单据审核里，如果只想读取单据并防止审核过程中被别人改，可以使用当前读：

```sql
START TRANSACTION;

SELECT id, status, total_amount
FROM scm_purchase_order
WHERE id = 9001
FOR UPDATE;

UPDATE scm_purchase_order
SET status = 'APPROVED'
WHERE id = 9001 AND status = 'WAIT_APPROVE';

COMMIT;
```

`FOR UPDATE` 会对命中的记录加排他锁。其他事务如果也想审核这张采购单，会等待当前事务提交或回滚。这里的重点是事务范围要短：查单据、校验状态、更新状态、写审核日志，然后立刻提交。不要在持锁事务里调用远程接口、发送消息或执行复杂报表。

## 锁和索引的关系

InnoDB 行锁是加在索引上的。是否命中合适索引，直接决定锁的范围。

下面这条 SQL 如果能命中 `uk_wh_sku`，通常只会锁住目标 SKU 的库存记录：

```sql
SELECT *
FROM scm_inventory
WHERE warehouse_id = 1 AND sku_id = 1001
FOR UPDATE;
```

如果查询条件没有索引，比如按一个低选择性的字段查库存：

```sql
SELECT *
FROM scm_inventory
WHERE batch_status = 'AVAILABLE'
FOR UPDATE;
```

数据库可能扫描大量记录，并在扫描过程中对更多索引记录加锁。结果就是一个库存预占请求把无关 SKU 也阻塞了。供应链系统里，库存、批次、库位这些表必须按业务唯一性和高频查询路径设计索引，否则锁问题会被放大。

## 业务建模建议

库存扣减建议优先使用“条件更新 + 影响行数判断”，不要在应用层先查库存再扣库存。

单据审核建议使用状态机约束：

```sql
UPDATE scm_purchase_order
SET status = 'APPROVED',
    approved_by = 101,
    approved_at = NOW()
WHERE id = 9001
  AND status = 'WAIT_APPROVE';
```

这类 SQL 天然具备幂等特征。重复审核时，第二次更新影响行数为 0，应用层可以返回“状态已变更”。

对于金额结算、库存转移这类强一致流程，悲观锁是合理选择。但对读多写少、冲突概率低的配置类数据，比如供应商报价、运输模板，可以考虑乐观锁，用 `version` 控制并发覆盖。

## 排查时看什么

线上出现锁等待时，先确认三个事实：

- 哪个事务在等。
- 它等的是哪张表、哪个索引、哪类锁。
- 持锁事务正在执行什么 SQL，为什么还没提交。

常用命令：

```sql
SHOW PROCESSLIST;
SHOW ENGINE INNODB STATUS;

SELECT *
FROM performance_schema.data_locks;

SELECT *
FROM performance_schema.data_lock_waits;
```

如果 MySQL 版本较老，没有 `performance_schema.data_locks`，就重点看 `SHOW ENGINE INNODB STATUS` 里的 latest detected deadlock 和 transaction 信息。

## 小结

MySQL 锁的本质是数据库给并发事务安排修改顺序。供应链系统的库存、单据、批次、结算都依赖这个顺序。写业务代码时，要把锁设计落实到 SQL：使用明确索引、缩短事务、用状态条件保护更新、避免持锁做慢操作。能做到这些，锁就不是线上事故的来源，而是业务一致性的基础设施。
