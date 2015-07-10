
/* Drop Tables */

DROP TABLE IF EXISTS tbl2_site_relation;
DROP TABLE IF EXISTS OSG_DATA_ITEM_PICTURE;
DROP TABLE IF EXISTS OSG_ITEM_CAMERA;
DROP TABLE IF EXISTS OSG_CAMERA;
DROP TABLE IF EXISTS tbl2_object_material;
DROP TABLE IF EXISTS OSG_DATA_ITEM_MESH;
DROP TABLE IF EXISTS OSG_DATA_ITEM_PC_SITE;
DROP TABLE IF EXISTS OSG_DATA_ITEM;
DROP TABLE IF EXISTS tbl2_object_depression;
DROP TABLE IF EXISTS tbl2_object_decoration;
DROP TABLE IF EXISTS tbl1_object;
DROP TABLE IF EXISTS tbl1_site;
DROP TABLE IF EXISTS RAW_DATA_ITEM_PICTURE;
DROP TABLE IF EXISTS NEXUS_DATA_ITEM_MESH;
DROP TABLE IF EXISTS RAW_DATA_ITEM_MESH;
DROP TABLE IF EXISTS POTREE_DATA_ITEM_PC;
DROP TABLE IF EXISTS OSG_DATA_ITEM_PC_BACKGROUND;
DROP TABLE IF EXISTS RAW_DATA_ITEM_PC;
DROP TABLE IF EXISTS RAW_DATA_ITEM;
DROP TABLE IF EXISTS OSG_ITEM_OBJECT;
DROP TABLE IF EXISTS ITEM_OBJECT;
DROP TABLE IF EXISTS ITEM;
DROP TABLE IF EXISTS OSG_LABEL;
DROP TABLE IF EXISTS OSG_LOCATION;




/* Create Tables */

CREATE TABLE tbl2_site_relation
(
	id int NOT NULL,
	site_id int NOT NULL,
	related_site_id int NOT NULL,
	reliability varchar(255),
	remarks varchar(255),
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE OSG_DATA_ITEM_PICTURE
(
	osg_data_item_id int NOT NULL,
	raw_data_item_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE OSG_CAMERA
(
	osg_camera_name text NOT NULL,
	osg_location_id int NOT NULL,
	PRIMARY KEY (osg_camera_name)
) WITHOUT OIDS;


CREATE TABLE OSG_ITEM_CAMERA
(
	item_id int NOT NULL,
	osg_camera_name text NOT NULL
) WITHOUT OIDS;


CREATE TABLE tbl2_object_material
(
	id int NOT NULL,
	site_id int NOT NULL,
	object_id int NOT NULL,
	material_type varchar(255),
	material_subtype varchar(255),
	material_technique varchar(255),
	date_entry timestamp,
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE OSG_DATA_ITEM
(
	osg_data_item_id serial NOT NULL,
	osg_location_id int NOT NULL,
	abs_path text NOT NULL,
	xml_abs_path text NOT NULL,
	last_mod int,
	last_check int,
	PRIMARY KEY (osg_data_item_id)
) WITHOUT OIDS;


CREATE TABLE tbl1_object
(
	site_id int NOT NULL,
	object_id int NOT NULL,
	in_situ boolean,
	ancient boolean,
	condition varchar(255),
	modern_restoration boolean,
	description_object text,
	object_type varchar(255),
	object_interpretation_list varchar(255),
	object_interpretation varchar(255),
	period varchar(255),
	date_specific varchar(255),
	material_remarks text,
	date_entry timestamp,
	description_restorations varchar(255),
	UNIQUE (site_id, object_id)
) WITHOUT OIDS;


CREATE TABLE ITEM
(
	item_id int NOT NULL,
	background boolean NOT NULL,
	geom polygon,
	min_z float DEFAULT 0 NOT NULL,
	max_z float DEFAULT 0 NOT NULL,
	PRIMARY KEY (item_id)
) WITHOUT OIDS;


CREATE TABLE OSG_LOCATION
(
	osg_location_id serial NOT NULL,
	srid int,
	x double precision,
	y double precision,
	z double precision,
	xs double precision DEFAULT 1,
	ys double precision DEFAULT 1,
	zs double precision DEFAULT 1,
	h double precision DEFAULT 0,
	p double precision DEFAULT 0,
	r double precision DEFAULT 0,
	cast_shadow boolean,
	PRIMARY KEY (osg_location_id)
) WITHOUT OIDS;


CREATE TABLE OSG_LABEL
(
	osg_label_name text NOT NULL,
	osg_location_id int NOT NULL,
	text text NOT NULL,
	red float NOT NULL,
	green float NOT NULL,
	blue float NOT NULL,
	rotate_screen boolean,
	outline boolean,
	font text,
	PRIMARY KEY (osg_label_name)
) WITHOUT OIDS;


CREATE TABLE OSG_DATA_ITEM_MESH
(
	osg_data_item_id int NOT NULL,
	raw_data_item_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE tbl2_object_depression
(
	id int NOT NULL,
	site_id int NOT NULL,
	object_id int NOT NULL,
	depression_type varchar(255),
	amount int,
	measurements varchar(255),
	date_entry timestamp,
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE RAW_DATA_ITEM
(
	raw_data_item_id serial NOT NULL,
	item_id int NOT NULL,
	abs_path text NOT NULL,
	srid int,
	last_mod int,
	last_check int,
	PRIMARY KEY (raw_data_item_id)
) WITHOUT OIDS;


CREATE TABLE POTREE_DATA_ITEM_PC
(
	potree_data_item_pc_id serial NOT NULL,
	raw_data_item_id int NOT NULL,
	abs_path text NOT NULL,
	last_mod int,
	last_check int,
	number_levels int,
	PRIMARY KEY (potree_data_item_pc_id)
) WITHOUT OIDS;


CREATE TABLE tbl2_object_decoration
(
	id int NOT NULL,
	site_id int NOT NULL,
	object_id int NOT NULL,
	decoration_type varchar(255),
	depiction varchar(255),
	doric boolean,
	ionic boolean,
	corinthian boolean,
	composite boolean,
	tuscan boolean,
	unknow boolean,
	date_entry timestamp,
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE ITEM_OBJECT
(
	item_id int NOT NULL,
	object_number int NOT NULL,
	CONSTRAINT site_object_unique UNIQUE (item_id, object_number)
) WITHOUT OIDS;


CREATE TABLE RAW_DATA_ITEM_PC
(
	raw_data_item_id int NOT NULL,
	number_points int NOT NULL,
	extension varchar(3) NOT NULL,
	minx double precision NOT NULL,
	miny double precision NOT NULL,
	minz double precision NOT NULL,
	maxx double precision NOT NULL,
	maxy double precision NOT NULL,
	maxz double precision NOT NULL,
	color_8bit boolean NOT NULL,
	PRIMARY KEY (raw_data_item_id)
) WITHOUT OIDS;


CREATE TABLE OSG_DATA_ITEM_PC_BACKGROUND
(
	osg_data_item_pc_background_id serial NOT NULL,
	raw_data_item_id int NOT NULL,
	abs_path text NOT NULL,
	offset_x double precision,
	offset_y double precision,
	offset_z double precision,
	last_mod int,
	last_check int,
	PRIMARY KEY (osg_data_item_pc_background_id)
) WITHOUT OIDS;


CREATE TABLE OSG_DATA_ITEM_PC_SITE
(
	osg_data_item_id int NOT NULL,
	raw_data_item_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE RAW_DATA_ITEM_PICTURE
(
	raw_data_item_id int NOT NULL,
	current_picture boolean NOT NULL,
	thumbnail boolean NOT NULL,
	x double precision,
	y double precision,
	z double precision,
	dx double precision,
	dy double precision,
	dz double precision,
	ux double precision,
	uy double precision,
	uz double precision,
	PRIMARY KEY (raw_data_item_id)
) WITHOUT OIDS;


CREATE TABLE tbl1_site
(
	site_id int NOT NULL,
	administrator varchar(255),
	modern_composition boolean,
	description_site text,
	site_context varchar(255),
	site_interpretation_keyword varchar(255),
	site_interpretation text,
	date_entry timestamp,
	description_m_composition varchar(255),
	PRIMARY KEY (site_id)
) WITHOUT OIDS;


CREATE TABLE OSG_ITEM_OBJECT
(
	item_id int NOT NULL,
	object_number int NOT NULL,
	osg_location_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE NEXUS_DATA_ITEM_MESH
(
	nexus_data_item_mesh_id serial NOT NULL,
	raw_data_item_id int NOT NULL,
	abs_path text NOT NULL,
	last_mod int,
	last_check int,
	PRIMARY KEY (nexus_data_item_mesh_id)
) WITHOUT OIDS;


CREATE TABLE RAW_DATA_ITEM_MESH
(
	raw_data_item_id int NOT NULL,
	obj_abs_path text,
	ply_abs_path text,
	mtl_abs_path text,
	current_mesh boolean NOT NULL,
	color_8bit boolean NOT NULL,
	PRIMARY KEY (raw_data_item_id)
) WITHOUT OIDS;



/* Create Foreign Keys */

ALTER TABLE OSG_ITEM_CAMERA
	ADD FOREIGN KEY (osg_camera_name)
	REFERENCES OSG_CAMERA (osg_camera_name)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_PICTURE
	ADD FOREIGN KEY (osg_data_item_id)
	REFERENCES OSG_DATA_ITEM (osg_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_MESH
	ADD FOREIGN KEY (osg_data_item_id)
	REFERENCES OSG_DATA_ITEM (osg_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_PC_SITE
	ADD FOREIGN KEY (osg_data_item_id)
	REFERENCES OSG_DATA_ITEM (osg_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_object_depression
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES tbl1_object (site_id, object_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_object_decoration
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES tbl1_object (site_id, object_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_object_material
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES tbl1_object (site_id, object_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl1_site
	ADD FOREIGN KEY (site_id)
	REFERENCES ITEM (item_id)
	ON UPDATE NO ACTION
	ON DELETE NO ACTION
;


ALTER TABLE RAW_DATA_ITEM
	ADD FOREIGN KEY (item_id)
	REFERENCES ITEM (item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE ITEM_OBJECT
	ADD FOREIGN KEY (item_id)
	REFERENCES ITEM (item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_ITEM_CAMERA
	ADD FOREIGN KEY (item_id)
	REFERENCES ITEM (item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_CAMERA
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_ITEM_OBJECT
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_LABEL
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE RAW_DATA_ITEM_PICTURE
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE RAW_DATA_ITEM_MESH
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE RAW_DATA_ITEM_PC
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl1_object
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES ITEM_OBJECT (item_id, object_number)
	ON UPDATE NO ACTION
	ON DELETE NO ACTION
;


ALTER TABLE OSG_ITEM_OBJECT
	ADD FOREIGN KEY (item_id, object_number)
	REFERENCES ITEM_OBJECT (item_id, object_number)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE POTREE_DATA_ITEM_PC
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_PC (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_PC_BACKGROUND
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_PC (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_PC_SITE
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_PC (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_PICTURE
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_PICTURE (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_site_relation
	ADD FOREIGN KEY (site_id)
	REFERENCES tbl1_site (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl1_object
	ADD FOREIGN KEY (site_id)
	REFERENCES tbl1_site (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_site_relation
	ADD FOREIGN KEY (related_site_id)
	REFERENCES tbl1_site (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_DATA_ITEM_MESH
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_MESH (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE NEXUS_DATA_ITEM_MESH
	ADD FOREIGN KEY (raw_data_item_id)
	REFERENCES RAW_DATA_ITEM_MESH (raw_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;



