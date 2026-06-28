---
title: MyBatis入门：从SQL映射到供应链库存查询
date: 2016-04-10 21:10:08
tags: [Java, MyBatis, SQL, 库存系统, 供应链系统]
---

MyBatis 是 Java 后端常用的持久层框架。它不像 JPA 那样尽量屏蔽 SQL，而是把 SQL 显式交给开发者管理，再提供参数绑定、结果映射、动态 SQL、Mapper 接口等能力。对于供应链系统来说，订单、库存、仓储、采购、结算等模块经常需要精细控制 SQL，MyBatis 很适合这类场景。

## 整体流程

![MyBatis SQL 映射流程](/images/tech-flowcharts/mybatis-sql-mapping-flow.svg)

## MyBatis 解决什么问题

直接使用 JDBC 时，开发者通常要重复处理连接、预编译 SQL、参数绑定、结果集转换和资源关闭。MyBatis 把这些模板代码收敛起来，让开发者把注意力放在 SQL 和对象映射上。

核心能力包括：

1. Mapper 接口：用 Java 方法表达一次数据库操作。
2. XML 或注解 SQL：显式管理 SQL，便于优化。
3. 参数绑定：避免手工拼接 SQL，降低 SQL 注入风险。
4. 结果映射：把查询结果转换成 Java 对象。
5. 动态 SQL：根据条件生成不同查询。

## 供应链例子：库存查询

先定义库存表：

```sql
CREATE TABLE scm_inventory (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  warehouse_id BIGINT NOT NULL,
  sku_id BIGINT NOT NULL,
  available_qty INT NOT NULL,
  locked_qty INT NOT NULL,
  updated_at DATETIME NOT NULL,
  UNIQUE KEY uk_warehouse_sku (warehouse_id, sku_id)
);
```

Java 对象：

```java
public class InventoryRecord {
    private Long id;
    private Long warehouseId;
    private Long skuId;
    private Integer availableQty;
    private Integer lockedQty;
    private LocalDateTime updatedAt;
}
```

Mapper 接口：

```java
public interface InventoryMapper {
    InventoryRecord findByWarehouseAndSku(@Param("warehouseId") Long warehouseId,
                                          @Param("skuId") Long skuId);
}
```

XML 映射：

```xml
<mapper namespace="com.example.inventory.InventoryMapper">
    <resultMap id="InventoryRecordMap" type="com.example.inventory.InventoryRecord">
        <id property="id" column="id"/>
        <result property="warehouseId" column="warehouse_id"/>
        <result property="skuId" column="sku_id"/>
        <result property="availableQty" column="available_qty"/>
        <result property="lockedQty" column="locked_qty"/>
        <result property="updatedAt" column="updated_at"/>
    </resultMap>

    <select id="findByWarehouseAndSku" resultMap="InventoryRecordMap">
        SELECT id, warehouse_id, sku_id, available_qty, locked_qty, updated_at
        FROM scm_inventory
        WHERE warehouse_id = #{warehouseId}
          AND sku_id = #{skuId}
    </select>
</mapper>
```

这里的 `#{}` 是预编译参数绑定，不是字符串拼接。它会交给 JDBC PreparedStatement 处理，能避免大部分 SQL 注入风险。

## 动态 SQL

供应链系统经常有多条件查询，例如按仓库、SKU、是否低库存过滤：

```java
public class InventoryQuery {
    private Long warehouseId;
    private Long skuId;
    private Boolean onlyLowStock;
}
```

动态 SQL：

```xml
<select id="search" resultMap="InventoryRecordMap">
    SELECT id, warehouse_id, sku_id, available_qty, locked_qty, updated_at
    FROM scm_inventory
    <where>
        <if test="warehouseId != null">
            AND warehouse_id = #{warehouseId}
        </if>
        <if test="skuId != null">
            AND sku_id = #{skuId}
        </if>
        <if test="onlyLowStock != null and onlyLowStock">
            AND available_qty &lt; 10
        </if>
    </where>
    ORDER BY updated_at DESC
    LIMIT 100
</select>
```

`<where>` 会自动处理多余的 `AND`，比在 Java 里拼接字符串更清晰。

## 常见误区

第一，`#{}` 和 `${}` 不能混用。`#{}` 是参数绑定，`${}` 是文本替换。只有表名、排序字段这类无法预编译的位置才可能使用 `${}`，并且必须做白名单校验。

```java
private static final Set<String> ALLOWED_SORT_FIELDS =
        Set.of("updated_at", "available_qty", "locked_qty");
```

第二，Mapper 方法不要返回过大的集合。库存流水、订单流水、报表明细必须分页查询，否则容易造成堆内存压力。

第三，SQL 要命中索引。比如 `warehouse_id + sku_id` 是库存查询的高频条件，就应该建立联合唯一索引。

## 小结

MyBatis 的价值在于让 SQL 可控，同时减少 JDBC 模板代码。供应链系统的数据一致性和查询性能很依赖 SQL 质量，因此掌握 Mapper、结果映射、动态 SQL、参数绑定和索引配合，是使用 MyBatis 的基础能力。
