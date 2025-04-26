-- 修改 movies 表中 release_date 字段的长度
ALTER TABLE movies MODIFY COLUMN release_date VARCHAR(200); 