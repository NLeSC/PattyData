
/* Drop Tables */

DROP TABLE IF EXISTS tbl2_site_relation;
DROP TABLE IF EXISTS OSG_SITE_PC;
DROP TABLE IF EXISTS OSG_SITE_PICTURE;
DROP TABLE IF EXISTS ALIGNED_SITE_MESH;
DROP TABLE IF EXISTS OSG_SITE_OBJECT;
DROP TABLE IF EXISTS tbl2_object_depression;
DROP TABLE IF EXISTS tbl2_object_material;
DROP TABLE IF EXISTS tbl2_object_decoration;
DROP TABLE IF EXISTS tbl1_object;
DROP TABLE IF EXISTS SITE_OBJECT;
DROP TABLE IF EXISTS OSG_SITE_CAMERA;
DROP TABLE IF EXISTS OSG_CAMERA;
DROP TABLE IF EXISTS tbl1_site;
DROP TABLE IF EXISTS OSG_SITE_MESH;
DROP TABLE IF EXISTS OSG_SITE_DATA_ITEM;
DROP TABLE IF EXISTS ALIGNED_SITE_PC;
DROP TABLE IF EXISTS SITE_PICTURE;
DROP TABLE IF EXISTS POTREE_SITE_PC;
DROP TABLE IF EXISTS OSG_SITE_BACKGROUND_PC;
DROP TABLE IF EXISTS SITE_PC;
DROP TABLE IF EXISTS SITE_MESH;
DROP TABLE IF EXISTS SITE_DATA_ITEM;
DROP TABLE IF EXISTS SITE;
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


CREATE TABLE OSG_SITE_PC
(
	osg_site_data_item_id int NOT NULL,
	site_pc_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_PICTURE
(
	osg_site_data_item_id int NOT NULL,
	site_picture_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE ALIGNED_SITE_MESH
(
	site_mesh_id int NOT NULL,
	site_pc_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE SITE_OBJECT
(
	site_id int NOT NULL,
	object_number int NOT NULL,
	CONSTRAINT site_object UNIQUE (site_id, object_number)
) WITHOUT OIDS;


CREATE TABLE OSG_CAMERA
(
	osg_camera_name text NOT NULL,
	osg_location_id int NOT NULL,
	PRIMARY KEY (osg_camera_name)
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_CAMERA
(
	site_id int NOT NULL,
	osg_camera_name text NOT NULL
) WITHOUT OIDS;


CREATE TABLE tbl1_site
(
	site_id int,
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


CREATE TABLE tbl2_object_material
(
	id int NOT NULL,
	site_id int,
	object_id int,
	material_type varchar(255),
	material_subtype varchar(255),
	material_technique varchar(255),
	date_entry timestamp,
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_DATA_ITEM
(
	osg_site_data_item_id serial NOT NULL,
	osg_location_id int NOT NULL,
	abs_path text NOT NULL,
	xml_abs_path text NOT NULL,
	cast_shadow boolean,
	last_mod int,
	last_check int,
	PRIMARY KEY (osg_site_data_item_id)
) WITHOUT OIDS;


CREATE TABLE tbl1_object
(
	site_id int,
	object_id int,
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


CREATE TABLE ALIGNED_SITE_PC
(
	site_pc_id int NOT NULL,
	site_background_pc_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE SITE_PICTURE
(
	site_picture_id int NOT NULL,
	current_picture boolean NOT NULL,
	thumbnail boolean NOT NULL,
	srid int,
	x float,
	y float,
	z float,
	dx float,
	dy float,
	dz float,
	PRIMARY KEY (site_picture_id)
) WITHOUT OIDS;


CREATE TABLE SITE
(
	site_id int NOT NULL,
	background boolean NOT NULL,
	geom polygon,
	PRIMARY KEY (site_id)
) WITHOUT OIDS;


CREATE TABLE OSG_LOCATION
(
	osg_location_id serial NOT NULL,
	srid int,
	x float,
	y float,
	z float,
	xs float,
	ys float,
	zs float,
	h float,
	p float,
	r float,
	cast_shadow boolean,
	PRIMARY KEY (osg_location_id)
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_OBJECT
(
	site_id int NOT NULL,
	object_number int NOT NULL,
	osg_location_id int NOT NULL
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


CREATE TABLE SITE_PC
(
	site_pc_id int NOT NULL,
	srid int,
	number_points int NOT NULL,
	extension varchar(3) NOT NULL,
	minx double precision NOT NULL,
	miny double precision NOT NULL,
	minz double precision NOT NULL,
	maxx double precision NOT NULL,
	maxy double precision NOT NULL,
	maxz double precision NOT NULL,
	color_8bit boolean NOT NULL,
	PRIMARY KEY (site_pc_id)
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_MESH
(
	osg_site_data_item_id int NOT NULL,
	site_mesh_id int NOT NULL
) WITHOUT OIDS;


CREATE TABLE tbl2_object_depression
(
	id int NOT NULL,
	site_id int,
	object_id int,
	depression_type varchar(255),
	amount int,
	measurements varchar(255),
	date_entry timestamp,
	PRIMARY KEY (id)
) WITHOUT OIDS;


CREATE TABLE SITE_DATA_ITEM
(
	site_data_item_id serial NOT NULL,
	site_id int NOT NULL,
	abs_path text NOT NULL,
	last_mod int,
	last_check int,
	PRIMARY KEY (site_data_item_id)
) WITHOUT OIDS;


CREATE TABLE SITE_MESH
(
	site_mesh_id int NOT NULL,
	current_mesh boolean NOT NULL,
	PRIMARY KEY (site_mesh_id)
) WITHOUT OIDS;


CREATE TABLE POTREE_SITE_PC
(
	pc_potree_site_id serial NOT NULL,
	site_pc_id int NOT NULL,
	asb_path text,
	last_mod int,
	last_check int,
	number_levels int,
	spacing float,
	PRIMARY KEY (pc_potree_site_id)
) WITHOUT OIDS;


CREATE TABLE OSG_SITE_BACKGROUND_PC
(
	osg_site_background_pc_id serial NOT NULL,
	site_pc_id int NOT NULL,
	abs_path text NOT NULL,
	offset_x float,
	offset_y float,
	offset_z float,
	last_mod int,
	last_check int,
	PRIMARY KEY (osg_site_background_pc_id)
) WITHOUT OIDS;


CREATE TABLE tbl2_object_decoration
(
	id int NOT NULL,
	site_id int,
	object_id int,
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



/* Create Foreign Keys */

ALTER TABLE OSG_SITE_OBJECT
	ADD FOREIGN KEY (site_id, object_number)
	REFERENCES SITE_OBJECT (site_id, object_number)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl1_object
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES SITE_OBJECT (site_id, object_number)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_CAMERA
	ADD FOREIGN KEY (osg_camera_name)
	REFERENCES OSG_CAMERA (osg_camera_name)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_site_relation
	ADD FOREIGN KEY (related_site_id)
	REFERENCES tbl1_site (site_id)
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


ALTER TABLE OSG_SITE_PICTURE
	ADD FOREIGN KEY (osg_site_data_item_id)
	REFERENCES OSG_SITE_DATA_ITEM (osg_site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_MESH
	ADD FOREIGN KEY (osg_site_data_item_id)
	REFERENCES OSG_SITE_DATA_ITEM (osg_site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_PC
	ADD FOREIGN KEY (osg_site_data_item_id)
	REFERENCES OSG_SITE_DATA_ITEM (osg_site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl2_object_depression
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


ALTER TABLE tbl2_object_decoration
	ADD FOREIGN KEY (site_id, object_id)
	REFERENCES tbl1_object (site_id, object_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_PICTURE
	ADD FOREIGN KEY (site_picture_id)
	REFERENCES SITE_PICTURE (site_picture_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_DATA_ITEM
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE tbl1_site
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_OBJECT
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_CAMERA
	ADD FOREIGN KEY (site_id)
	REFERENCES SITE (site_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_DATA_ITEM
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_OBJECT
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


ALTER TABLE OSG_CAMERA
	ADD FOREIGN KEY (osg_location_id)
	REFERENCES OSG_LOCATION (osg_location_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_PC
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE ALIGNED_SITE_PC
	ADD FOREIGN KEY (site_background_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE POTREE_SITE_PC
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE ALIGNED_SITE_PC
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE ALIGNED_SITE_MESH
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_BACKGROUND_PC
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_PC (site_pc_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_PC
	ADD FOREIGN KEY (site_pc_id)
	REFERENCES SITE_DATA_ITEM (site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_MESH
	ADD FOREIGN KEY (site_mesh_id)
	REFERENCES SITE_DATA_ITEM (site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE SITE_PICTURE
	ADD FOREIGN KEY (site_picture_id)
	REFERENCES SITE_DATA_ITEM (site_data_item_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE ALIGNED_SITE_MESH
	ADD FOREIGN KEY (site_mesh_id)
	REFERENCES SITE_MESH (site_mesh_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;


ALTER TABLE OSG_SITE_MESH
	ADD FOREIGN KEY (site_mesh_id)
	REFERENCES SITE_MESH (site_mesh_id)
	ON UPDATE RESTRICT
	ON DELETE RESTRICT
;



