title: mybatis【入门】
date: 2016-04-10 21:10:08
tags: [技术文章]
---
## 什么是MyBatis

Spring是一个开源框架，它由Rod Johnson创建。它是为了解决企业应用开发的复杂性而创建的。

> MyBatis 本是apache的一个开源项目iBatis, 2010年这个项目由apache software foundation 迁移到了google code，并且改名为MyBatis。是一个基于Java的持久层框架

## 为什么我们要用Mybatis？

无论是Mybatis、Hibernate都是ORM的一种实现框架，都是对JDBC的一种封装！

![](https://i.imgur.com/pUCRpyB.png)

我们已经在持久层中学了几种技术了…
* Hibernate
* jdbc
* SpringDAO

那我们为啥还要学Mybatis呢？？？现在Mybatis在业内大行其道，那为啥他能那么火呢？？

Hibernate是一个比较老旧的框架，用过他的同学都知道，只要你会用，用起来十分舒服…啥sql代码都不用写…但是呢，它也是有的缺点：：处理复杂业务时，灵活度差, 复杂的HQL难写难理解，例如多表查询的HQL语句

而JDBC很容易理解，就那么几个固定的步骤，就是开发起来太麻烦了，因为什么都要我们自己干

而SpringDAO其实就是JDBC的一层封装，就类似于dbutils一样，没有特别出彩的地方

我们可以认为，Mybatis就是jdbc和Hibernate之间的一个平衡点…毕竟现在业界都是用这个框架，我们也不能不学呀！

## Mybatis快速入门

我们已经学过了Hibernate了，对于Mybatis入门其实就非常类似的，因此就很简单就能掌握基本的开发了。

#### 导入开发包

导入Mybatis开发包

* mybatis-3.1.1.jar
* commons-logging-1.1.1.jar
* log4j-1.2.16.jar
* cglib-2.2.2.jar
* asm-3.3.1.jar

导入mysql/oracle开发包

* mysql-connector-java-5.1.7-bin.jar
* Oracle 11g 11.2.0.1.0 JDBC_ojdbc6.jar

#### 准备测试工作

创建一张表:

    create table students(
      id  int(5) primary key,
      name varchar(10),
      sal double(8,2)
    );
    
创建实体：

    /**
     * Created by xing on 2017/7/21.
     */
    
    public class Student {
        private Integer id;
        private String name;
        private Double sal;
    
        public Student() {
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
    }
    
#### 创建mybatis配置文件

创建mybatis的配置文件，配置数据库的信息,数据库我们可以配置多个，但是默认的只能用一个.

    <?xml version="1.0" encoding="UTF-8"?>
    <!DOCTYPE configuration PUBLIC "-//mybatis.org//DTD Config 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-config.dtd">
    
    <configuration>
    
    
        <!-- 加载类路径下的属性文件 -->
        <properties resource="db.properties"/>
    
        <!-- 设置一个默认的连接环境信息 -->
        <environments default="mysql_developer">
            <!-- 连接环境信息，取一个任意唯一的名字 -->
            <environment id="mysql_developer">
                <!-- mybatis使用jdbc事务管理方式 -->
                <transactionManager type="jdbc"/>
                <!-- mybatis使用连接池方式来获取连接 -->
                <dataSource type="pooled">
                    <!-- 配置与数据库交互的4个必要属性 -->
                    <property name="driver" value="${mysql.driver}"/>
                    <property name="url" value="${mysql.url}"/>
                    <property name="username" value="${mysql.username}"/>
                    <property name="password" value="${mysql.password}"/>
                </dataSource>
            </environment>
    
    
            <!-- 连接环境信息，取一个任意唯一的名字 -->
            <environment id="oracle_developer">
                <!-- mybatis使用jdbc事务管理方式 -->
                <transactionManager type="jdbc"/>
                <!-- mybatis使用连接池方式来获取连接 -->
                <dataSource type="pooled">
                    <!-- 配置与数据库交互的4个必要属性 -->
                    <property name="driver" value="${oracle.driver}"/>
                    <property name="url" value="${oracle.url}"/>
                    <property name="username" value="${oracle.username}"/>
                    <property name="password" value="${oracle.password}"/>
                </dataSource>
            </environment>
        </environments>
    
    
    </configuration>
    
#### 编写工具类测试是否获取到连接

使用Mybatis的API来创建一个工具类，通过mybatis配置文件与数据库的信息，得到Connection对象

    package cn.javaee.mybatis.util;
    
    import java.io.IOException;
    import java.io.Reader;
    import java.sql.Connection;
    import org.apache.ibatis.io.Resources;
    import org.apache.ibatis.session.SqlSession;
    import org.apache.ibatis.session.SqlSessionFactory;
    import org.apache.ibatis.session.SqlSessionFactoryBuilder;
    
    /**
     * 工具类
     * @author xing
     */
    public class MybatisUtil {
        private static ThreadLocal<SqlSession> threadLocal = new ThreadLocal<SqlSession>();
        private static SqlSessionFactory sqlSessionFactory;
        /**
         * 加载位于src/mybatis.xml配置文件
         */
        static{
            try {
                Reader reader = Resources.getResourceAsReader("mybatis.xml");
                sqlSessionFactory = new SqlSessionFactoryBuilder().build(reader);
            } catch (IOException e) {
                e.printStackTrace();
                throw new RuntimeException(e);
            }
        }
        /**
         * 禁止外界通过new方法创建 
         */
        private MybatisUtil(){}
        /**
         * 获取SqlSession
         */
        public static SqlSession getSqlSession(){
            //从当前线程中获取SqlSession对象
            SqlSession sqlSession = threadLocal.get();
            //如果SqlSession对象为空
            if(sqlSession == null){
                //在SqlSessionFactory非空的情况下，获取SqlSession对象
                sqlSession = sqlSessionFactory.openSession();
                //将SqlSession对象与当前线程绑定在一起
                threadLocal.set(sqlSession);
            }
            //返回SqlSession对象
            return sqlSession;
        }
        /**
         * 关闭SqlSession与当前线程分开
         */
        public static void closeSqlSession(){
            //从当前线程中获取SqlSession对象
            SqlSession sqlSession = threadLocal.get();
            //如果SqlSession对象非空
            if(sqlSession != null){
                //关闭SqlSession对象
                sqlSession.close();
                //分开当前线程与SqlSession对象的关系，目的是让GC尽早回收
                threadLocal.remove();
            }
        }   
        /**
         * 测试
         */
        public static void main(String[] args) {
            Connection conn = MybatisUtil.getSqlSession().getConnection();
            System.out.println(conn!=null?"连接成功":"连接失败");
        }
    }
    
#### 创建实体与映射关系文件

配置实体与表的映射关系

    <?xml version="1.0" encoding="UTF-8" ?>
    <!DOCTYPE mapper PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
    "http://mybatis.org/dtd/mybatis-3-mapper.dtd">
    
    <!-- namespace属性是名称空间，必须唯一 -->
    <mapper namespace="cn.com.Student">    
    
        <!-- resultMap标签:映射实体与表 
             type属性：表示实体全路径名
             id属性：为实体与表的映射取一个任意的唯一的名字
        -->
        <resultMap type="student" id="studentMap">
            <!-- id标签:映射主键属性
                 result标签：映射非主键属性
                 property属性:实体的属性名
                 column属性：表的字段名  
            -->                         
            <id property="id" column="id"/>
            <result property="name" column="name"/>
            <result property="sal" column="sal"/>
        </resultMap>
    
    </mapper>

现在我们已经有了Mybatis的配置文件和表与实体之前的映射文件了，因此我们要将配置文件和映射文件关联起来

    <mappers>
        <mapper resource="StudentMapper.xml"/>
    </mappers>
    
#### 编写DAO

    public class StudentDao {
    
    
        public void add(Student student) throws Exception {
            //得到连接对象
            SqlSession sqlSession = MybatisUtil.getSqlSession();
            sqlSession.insert();
        }
    
        public static void main(String[] args) throws Exception {
    
            StudentDao studentDao = new StudentDao();
    
            Student student = new Student(1, "zhongfucheng", 10000D);
            studentDao.add(student);
    
        }
    }
    
到现在为止，我们实体与表的映射文件仅仅映射了实体属性与表的字段的关系,而我们Mybatis是需要自己手动编写SQL代码,在实体与表的映射文件中写。

**==Mybatis实体与表的映射文件中提供了insert标签==【SQL代码片段】供我们使用**

    //在JDBC中我们通常使用?号作为占位符，而在Mybatis中，我们是使用#{}作为占位符
    //parameterType我们指定了传入参数的类型
    //#{}实际上就是调用了Student属性的get方法

    <insert id="add" parameterType="Student">

        INSERT INTO ZHONGFUCHENG.STUDENTS (ID, NAME, SAL) VALUES (#{id},#{name},#{sal});
    </insert>
    
在程序中调用映射文件的SQL代码片段

    public void add(Student student) throws Exception {
        //得到连接对象
        SqlSession sqlSession = MybatisUtil.getSqlSession();
        try{
            //映射文件的命名空间.SQL片段的ID，就可以调用对应的映射文件中的SQL
            sqlSession.insert("StudentID.add", student);
            sqlSession.commit();
        }catch(Exception e){
            e.printStackTrace();
            sqlSession.rollback();
            throw e;
        }finally{
            MybatisUtil.closeSqlSession();
        }
    }
    
值得注意的是：Mybatis中的事务是默认开启的，因此我们在完成操作以后，需要我们手动去提交事务！

#### Mybatis工作流程

* 通过Reader对象读取Mybatis映射文件
* 通过SqlSessionFactoryBuilder对象创建SqlSessionFactory对象
* 获取当前线程的SQLSession
* 事务默认开启
* 通过SQLSession读取映射文件中的操作编号，从而读取SQL语句
* 提交事务
* 关闭资源

#### Mybatis分页

分页是一个非常实用的技术点，我们也来学习一下使用Mybatis是怎么分页的!

我们的分页是需要多个参数的，并不是像我们之前的例子中只有一个参数。当需要接收多个参数的时候，我们使用Map集合来装载！

    public List<Student>  pagination(int start ,int end) throws Exception {
        //得到连接对象
        SqlSession sqlSession = MybatisUtil.getSqlSession();
        try{
            //映射文件的命名空间.SQL片段的ID，就可以调用对应的映射文件中的SQL


            /**
             * 由于我们的参数超过了两个，而方法中只有一个Object参数收集
             * 因此我们使用Map集合来装载我们的参数
             */
            Map<String, Object> map = new HashMap();
            map.put("start", start);
            map.put("end", end);
            return sqlSession.selectList("StudentID.pagination", map);
        }catch(Exception e){
            e.printStackTrace();
            sqlSession.rollback();
            throw e;
        }finally{
            MybatisUtil.closeSqlSession();
        }
    }
    public static void main(String[] args) throws Exception {
        StudentDao studentDao = new StudentDao();
        List<Student> students = studentDao.pagination(0, 3);
        for (Student student : students) {

            System.out.println(student.getId());

        }

    }

那么在实体与表映射文件中，我们接收的参数就是map集合

    <!--分页查询-->
    <select id="pagination" parameterType="map" resultMap="studentMap">

        /*根据key自动找到对应Map集合的value*/
        select * from students limit #{start},#{end};

    </select>
 
## Mapper代理方式

Mapper代理方式的意思就是：程序员只需要写dao接口，dao接口实现对象由mybatis自动生成代理对象。

我们可以发现DaoImpl是十分重复的：

* dao的实现类中存在重复代码，整个mybatis操作的过程代码模板重复（先创建sqlsession、调用sqlsession的方法、关闭sqlsession）
* dao的实现 类中存在硬编码，调用sqlsession方法时将statement的id硬编码。

以前的重复代码和硬编码如下：

    public class StudentDao {
    
        public void add(Student student) throws Exception {
            //得到连接对象
            SqlSession sqlSession = MybatisUtil.getSqlSession();
            try{
                //映射文件的命名空间.SQL片段的ID，就可以调用对应的映射文件中的SQL
                sqlSession.insert("StudentID.add", student);
                sqlSession.commit();
            }catch(Exception e){
                e.printStackTrace();
                sqlSession.rollback();
                throw e;
            }finally{
                MybatisUtil.closeSqlSession();
            }
        }
        public static void main(String[] args) throws Exception {
            StudentDao studentDao = new StudentDao();
            Student student = new Student(3, "zhong3", 10000D);
            studentDao.add(student);
        }
    }

#### Mapper开发规范

想要Mybatis帮我们自动生成Mapper代理的话，我们需要遵循以下的规范：
* mapper.xml中namespace指定为mapper接口的全限定名
  * 此步骤目的：通过mapper.xml和mapper.java进行关联
* mapper.xml中statement的id就是mapper.java中方法名
* mapper.xml中statement的parameterType和mapper.java中方法输入参数类型一致
* mapper.xml中statement的resultType和mapper.java中方法返回值类型一致

==**再次说明**：statement就是我们在mapper.xml文件中命名空间+sql指定的id==

#### Mapper代理返回值问题
mapper接口方法返回值：

* 如果是返回的单个对象，返回值类型是pojo类型，生成的代理对象内部通过selectOne获取记录
* 如果返回值类型是集合对象，生成的代理对象内部通过selectList获取记录

#### Mybatis解决JDBC编程的问题
* 数据库链接创建、释放频繁造成系统资源浪费从而影响系统性能，如果使用数据库链接池可解决此问题。
  * 解决：在SqlMapConfig.xml中配置数据链接池，使用连接池管理数据库链接。
* Sql语句写在代码中造成代码不易维护，实际应用sql变化的可能较大，sql变动需要改变java代码。
  * 解决：将Sql语句配置在XXXXmapper.xml文件中与java代码分离。
* 向sql语句传参数麻烦，因为sql语句的where条件不一定，可能多也可能少，占位符需要和参数一一对应。
  * 解决：Mybatis自动将java对象映射至sql语句，通过statement中的parameterType定义输入参数的类型。
* 对结果集解析麻烦，sql变化导致解析代码变化，且解析前需要遍历，如果能将数据库记录封装成pojo对象解析比较方便。
  * 解决：Mybatis自动将sql执行结果映射至java对象，通过statement中的resultType定义输出结果的类型。

## 总结

* Mybatis的准备工作与Hibernate差不多，都需要一个总配置文件、一个映射文件。
* Mybatis的SQLSession工具类使用ThreadLocal来对线程中的Session来进行管理。
* Mybatis的事务默认是开启的，需要我们手动去提交事务。
* Mybatis的SQL语句是需要手写的，在程序中通过映射文件的命名空间.sql语句的id来进行调用!
* 在Mybatis中，增删改查都是需要我们自己写SQL语句的，然后在程序中调用即可了。SQL由于是我们自己写的，于是就相对Hibernate灵活一些。
* 如果需要传入多个参数的话，那么我们一般在映射文件中用Map来接收。
由于我们在开发中会经常用到条件查询，Mybatis的话，我们是自己手写SQL代码的。
* Mapper的代理方式简化开发
  * 命名空间要与JavaBean的全类名相同
  * sql片段语句的id要与Dao接口的方法名相同
  * 方法的参数和返回值要与SQL片段的接收参数类型和返回类型相同