DROP TABLE cloud;
CREATE TABLE cloud(
    area varchar(16),
    form varchar(16),
    pc varchar(16),
    siteNum varchar(16),
    lx float8,
    ly float8,
    lz float8,
    ux float8,
    uy float8,
    uz float8,
    spacing float8,
    format varchar(16),
    octreeName varchar(32),
    data bytea
);

--DROP TABLE octree1;
--CREATE TABLE octree1(
--    nodename varchar(32),
--    npoints int,
--    data bytea
--);

