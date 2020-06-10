CREATE DATABASE IF NOT EXISTS patchman CHARACTER SET utf8 COLLATE utf8_general_ci;
GRANT ALL PRIVILEGES ON patchman.* TO 'patchman'@'%' IDENTIFIED BY 'patchman';
