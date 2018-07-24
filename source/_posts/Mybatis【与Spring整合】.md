title: Mybatis【与Spring整合】
date: 2016-04-11 20:36:29
tags: [技术文章]
---
#### 导入jar包

以下使用的是Oracle数据库来进行测试

* aopalliance.jar
* asm-3.3.1.jar
* aspectjweaver.jar
* c3p0-0.9.1.2.jar
* cglib-2.2.2.jar
* commons-logging.jar
* log4j-1.2.16.jar
* mybatis-3.1.1.jar
* mybatis-spring-1.1.1.jar
* mysql-connector-java-5.1.7-bin.jar
* ojdbc5.jar
* org.springframework.aop-3.0.5.RELEASE.jar
* org.springframework.asm-3.0.5.RELEASE.jar
* org.springframework.beans-3.0.5.RELEASE.jar
* org.springframework.context-3.0.5.RELEASE.jar
* org.springframework.core-3.0.5.RELEASE.jar
* org.springframework.expression-3.0.5.RELEASE.jar
* org.springframework.jdbc-3.0.5.RELEASE.jar
* org.springframework.orm-3.0.5.RELEASE.jar
* org.springframework.transaction-3.0.5.RELEASE.jar
* org.springframework.web.servlet-3.0.5.RELEASE.jar
* org.springframework.web-3.0.5.RELEASE.jar

#### 创建表

create table emps(
  eid number(5) primary key,
  ename varchar2(20),
  esal number(8,2),
  esex varchar2(2)
);

#### 创建实体

    package entity;
    
    /**
     * 员工
     * @author AdminTC
     */
    public class Emp {
        private Integer id;
        private String name;
        private Double sal;
        private String sex;
        public Emp(){}
        public Emp(Integer id, String name, Double sal, String sex) {
            this.id = id;
            this.name = name;
            this.sal = sal;
            this.sex = sex;
        }
        public Integer getId() {
            return id;
        }
        public void setId(Integer id) {
            this.id = id;
        }
        public String getName() {
            return name;
        }
        public void setName(String name) {
            this.name = name;
        }
        public Double getSal() {
            return sal;
        }
        public void setSal(Double sal) {
            this.sal = sal;
        }
        public String getSex() {
            return sex;
        }
        public void setSex(String sex) {
            this.sex = sex;
        }
    }

#### 创建实体与表的映射文件

<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
"http://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="empNamespace">

    <resultMap type="entity.Emp" id="empMap">
        <id property="id" column="eid"/>
        <result property="name" column="ename"/>
        <result property="sal" column="esal"/>
        <result property="sex" column="esex"/>
    </resultMap>    

    <!-- 增加员工 -->
    <insert id="add" parameterType="entity.Emp">
        insert into emps(eid,ename,esal,esex) values(#{id},#{name},#{sal},#{sex})
    </insert>

</mapper>

#### 创建Mybatis映射文件配置环境

数据库的信息交由Spring管理！Mybatis配置文件负责加载对应映射文件即可

    <configuration>
        <mappers>
            <mapper resource="zhongfucheng/entity/EmpMapper.xml"/>
    
        </mappers>
    </configuration>
    
#### 配置Spring核心过滤器【也是加载总配置文件】

    <!-- 核心springmvc核心控制器 -->
    <servlet>
        <servlet-name>DispatcherServlet</servlet-name>
        <servlet-class>org.springframework.web.servlet.DispatcherServlet</servlet-class>
        <init-param>
            <param-name>contextConfigLocation</param-name>
            <param-value>classpath:spring.xml</param-value>
        </init-param>
    </servlet>
    <servlet-mapping>
        <servlet-name>DispatcherServlet</servlet-name>
        <url-pattern>*.action</url-pattern>
    </servlet-mapping>
    
#### 配置数据库信息、事务

    <?xml version="1.0" encoding="UTF-8"?>
    <beans xmlns="http://www.springframework.org/schema/beans"
           xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:tx="http://www.springframework.org/schema/tx"
           xmlns:aop="http://www.springframework.org/schema/aop"
           xmlns:context="http://www.springframework.org/schema/context"
           xsi:schemaLocation="http://www.springframework.org/schema/beans http://www.springframework.org/schema/beans/spring-beans.xsd http://www.springframework.org/schema/tx http://www.springframework.org/schema/tx/spring-tx.xsd http://www.springframework.org/schema/aop http://www.springframework.org/schema/aop/spring-aop.xsd http://www.springframework.org/schema/context http://www.springframework.org/schema/context/spring-context.xsd">
    
    
        <!-- 配置C3P0连接池,目的：管理数据库连接 -->
        <bean id="comboPooledDataSourceID" class="com.mchange.v2.c3p0.ComboPooledDataSource">
            <property name="driverClass" value="oracle.jdbc.driver.OracleDriver"/>
            <property name="jdbcUrl" value="jdbc:oracle:thin:@127.0.0.1:1521:test"/>
            <property name="user" value="scott"/>
            <property name="password" value="tiger"/>
        </bean>
    
    
        <!-- 配置SqlSessionFactoryBean，目的：加载mybaits配置文件和映射文件，即替代原Mybatis工具类的作用 -->
        <bean id="sqlSessionFactoryBeanID" class="org.mybatis.spring.SqlSessionFactoryBean">
            <property name="configLocation" value="classpath:mybatis.xml"/>
            <property name="dataSource" ref="comboPooledDataSourceID"/>
        </bean>
    
    
        <!-- 配置Mybatis的事务管理器，即因为Mybatis底层用的是JDBC事务管事器，所以在这里依然配置JDBC事务管理器 -->
        <bean id="dataSourceTransactionManagerID" class="org.springframework.jdbc.datasource.DataSourceTransactionManager">
            <property name="dataSource" ref="comboPooledDataSourceID"/>
        </bean>
    
        <!-- 配置事务通知，即让哪些方法需要事务支持 -->
        <tx:advice id="tx" transaction-manager="dataSourceTransactionManagerID">
            <tx:attributes>
                <tx:method name="*" propagation="REQUIRED"/>
            </tx:attributes>
        </tx:advice>
    
        <!-- 配置事务切面，即让哪些包下的类需要事务 -->
        <aop:config>
            <aop:pointcut id="pointcut" expression="execution(* cn.com.service.*.*(..))"/>
            <aop:advisor advice-ref="tx" pointcut-ref="pointcut"/>
        </aop:config>
    
        <!--扫描注解-->
        <context:component-scan base-package="cn.com"/>
    
    
    </beans>
    
#### 创建Dao、Service、Action

    @Repository
    public class EmpDao {
        @Autowired
        private SqlSessionFactory sqlSessionFactory;
        /**
         * 增加员工
         */
        public void add(Emp emp) throws Exception {
            SqlSession sqlSession = sqlSessionFactory.openSession();
            sqlSession.insert("empNamespace.add", emp);
            sqlSession.close();
        }
    
    
    }
    
    @Service
    public class EmpService {
    
    
        @Autowired
        private zhongfucheng.dao.EmpDao empDao;
        public void addEmp(Emp emp) throws Exception {
            empDao.add(emp);
        }
    }
    
    @Controller
    @RequestMapping("/emp")
    public class EmpAction {
    
        @Autowired
        private EmpService empService;
    
        @RequestMapping("/register")
        public void register(Emp emp) throws Exception {
            empService.addEmp(emp);
            System.out.println("注册成功");
        }
    
    }
    
#### JSP页面测试

    <%@ page language="java" pageEncoding="UTF-8"%>
    <!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">
    <html>
      <head>
        <title>员工注册</title>
      </head>
      <body>
        <form action="${pageContext.request.contextPath}/emp/register.action" method="POST">
            <table border="2" align="center">
                <tr>
                    <th>编号</th>
                    <td><input type="text" name="id"></td>
                </tr>
                <tr>
                    <th>姓名</th>
                    <td><input type="text" name="name"></td>
                </tr>
                <tr>
                    <th>薪水</th>
                    <td><input type="text" name="sal"></td>
                </tr>
                <tr>
                    <th>性别</th>
                    <td>
                        <input type="radio" name="sex" value="男"/>男
                        <input type="radio" name="sex" value="女" checked/>女
                    </td>
                </tr>
                <tr>
                    <td colspan="2" align="center">
                        <input type="submit" value="注册"/>
                    </td>
                </tr>
            </table>
        </form>     
      </body>
    </html>

#### 总结

* web.xml加载Spring配置文件
* Spring配置文件配置数据连接池，SessionFactory、事务、扫描注解
* Mybatis总配置文件、实体以及相对应的映射文件
* 将映射文件加入到总配置文件中