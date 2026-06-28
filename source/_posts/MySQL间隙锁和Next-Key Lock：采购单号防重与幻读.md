---
title: MySQL间隙锁和Next-Key Lock：采购单号防重与幻读
date: 2025-04-10 09:45:00
tags: [MySQL, 间隙锁, Next-Key Lock, 幻读, 采购系统]
---

间隙锁是 MySQL 锁体系里最容易让人困惑的一类锁。它锁的不是已经存在的记录，而是索引记录之间的“空隙”。在 InnoDB 的可重复读隔离级别下，间隙锁和 Next-Key Lock 用来阻止其他事务在某个范围内插入新记录，从而避免当前读场景下的幻读。

供应链系统里，采购单号、入库批次号、结算期间号这类数据经常要求“范围内唯一”或“按规则递增”。如果只检查已有记录，不理解间隙锁，就很容易在高并发下出现重复单号或范围判断不一致。

## 间隙锁和防重流程

![MySQL 间隙锁和 Next-Key Lock 流程](/images/tech-flowcharts/mysql-next-key-phantom-flow.svg)

## 什么是幻读

假设采购系统要求同一个供应商在同一天不能创建重复外部单号：

```sql
CREATE TABLE scm_purchase_order (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  supplier_id BIGINT NOT NULL,
  external_no VARCHAR(64) NOT NULL,
  order_date DATE NOT NULL,
  status VARCHAR(32) NOT NULL,
  KEY idx_supplier_date_no (supplier_id, order_date, external_no)
) ENGINE=InnoDB;
```

事务 A 先检查不存在：

```sql
START TRANSACTION;

SELECT *
FROM scm_purchase_order
WHERE supplier_id = 2001
  AND order_date = '2025-04-10'
  AND external_no = 'PO-7788'
FOR UPDATE;
```

如果此时没有记录，事务 A 准备插入。事务 B 如果也执行同样检查，也可能看到不存在。两边都插入，就会重复。这就是典型的“先查再插”竞态。

## 用唯一约束解决第一层问题

防重复的第一选择不是依赖锁，而是唯一约束：

```sql
ALTER TABLE scm_purchase_order
ADD UNIQUE KEY uk_supplier_date_no (supplier_id, order_date, external_no);
```

然后直接插入：

```sql
INSERT INTO scm_purchase_order (
  supplier_id, order_date, external_no, status
) VALUES (
  2001, '2025-04-10', 'PO-7788', 'DRAFT'
);
```

如果并发重复插入，数据库会让一个成功，另一个失败。业务层捕获唯一键冲突，返回“采购单已存在”。这是最可靠、最容易维护的防重方案。

## 间隙锁适合什么场景

有些规则不是单点唯一，而是范围约束。比如一个供应商每天最多只能有 1000 张待审核采购单。检查时需要锁住某个范围，避免检查后别人插入新记录导致数量超过限制：

```sql
START TRANSACTION;

SELECT COUNT(*)
FROM scm_purchase_order
WHERE supplier_id = 2001
  AND order_date = '2025-04-10'
  AND status = 'WAIT_APPROVE'
FOR UPDATE;

-- 如果数量小于 1000，再插入
INSERT INTO scm_purchase_order (...);

COMMIT;
```

但这里有一个现实问题：`COUNT(*) FOR UPDATE` 在不同 MySQL 版本和执行计划下不一定按你想象的方式锁住范围。更稳的做法是把“当天供应商配额”抽成一条独立记录：

```sql
CREATE TABLE scm_supplier_daily_quota (
  supplier_id BIGINT NOT NULL,
  biz_date DATE NOT NULL,
  used_count INT NOT NULL,
  limit_count INT NOT NULL,
  PRIMARY KEY (supplier_id, biz_date)
) ENGINE=InnoDB;
```

然后更新这一行：

```sql
UPDATE scm_supplier_daily_quota
SET used_count = used_count + 1
WHERE supplier_id = 2001
  AND biz_date = '2025-04-10'
  AND used_count < limit_count;
```

影响行数为 1 才允许创建采购单。这个模型比依赖复杂范围锁更清晰。

## Next-Key Lock 是什么

Next-Key Lock 可以理解为记录锁加间隙锁。它既锁住已有索引记录，也锁住记录前面的间隙。范围查询当前读时，InnoDB 可能使用 Next-Key Lock 防止其他事务在范围内插入新记录。

例如：

```sql
SELECT *
FROM scm_purchase_order
WHERE supplier_id = 2001
  AND order_date >= '2025-04-01'
  AND order_date < '2025-05-01'
FOR UPDATE;
```

在可重复读隔离级别下，这类范围当前读可能锁住 4 月份相关索引范围，阻止其他事务插入该范围内的新采购单。锁范围取决于索引设计和执行计划。

如果索引是：

```sql
KEY idx_supplier_date (supplier_id, order_date)
```

锁范围会比没有该索引时更可控。没有合适索引时，范围锁可能扩大，甚至影响无关供应商。

## 供应链业务里的实践建议

第一，唯一性问题优先用唯一索引。比如采购外部单号、入库批次号、销售订单号。

第二，配额和计数问题优先抽象成计数行，用条件更新控制并发。不要用大范围 `COUNT FOR UPDATE` 扛高并发。

第三，必须范围锁时，必须设计和范围条件一致的联合索引。范围条件没有索引，间隙锁会变成线上阻塞源。

第四，不要把用户交互放在事务里。比如创建采购单时弹窗确认、调用供应商接口、远程校验合同，不能在持有范围锁期间执行。

## Demo：安全生成供应商日序号

如果采购单号规则是 `供应商 + 日期 + 序号`，可以用序号表控制：

```sql
CREATE TABLE scm_doc_sequence (
  doc_type VARCHAR(32) NOT NULL,
  biz_key VARCHAR(64) NOT NULL,
  current_value INT NOT NULL,
  PRIMARY KEY (doc_type, biz_key)
) ENGINE=InnoDB;
```

Java 代码：

```java
@Transactional
public String nextPurchaseNo(long supplierId, LocalDate date) {
    String bizKey = supplierId + ":" + date;
    int affected = sequenceMapper.increase("PURCHASE_ORDER", bizKey);
    if (affected == 0) {
        sequenceMapper.insert("PURCHASE_ORDER", bizKey, 1);
        return formatNo(supplierId, date, 1);
    }
    int value = sequenceMapper.current("PURCHASE_ORDER", bizKey);
    return formatNo(supplierId, date, value);
}
```

对应 SQL：

```sql
UPDATE scm_doc_sequence
SET current_value = current_value + 1
WHERE doc_type = #{docType}
  AND biz_key = #{bizKey};
```

真实项目里要处理并发首次插入的唯一键冲突。也可以先插入初始行，再统一更新。核心思想是把复杂范围竞争收敛到一条序号记录上。

## 小结

间隙锁和 Next-Key Lock 是 InnoDB 为范围一致性提供的机制，但业务系统不应该把所有防重和计数规则都寄托在隐式范围锁上。供应链系统更稳的建模是：唯一性用唯一索引，额度用计数行，序号用序号表，范围当前读必须配合明确索引。这样锁行为才可解释、可压测、可排查。
