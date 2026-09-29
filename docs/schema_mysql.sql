-- MySQL 8 reference DDL, compiled from SQLAlchemy models.
-- Use an empty it_service_desk database. Prefer flask init-db.
USE it_service_desk;



CREATE TABLE article (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	title VARCHAR(180) NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	body TEXT NOT NULL, 
	updated_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;


CREATE TABLE login_attempt (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	`key` VARCHAR(64) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id)
)

;

CREATE INDEX ix_login_attempt_key ON login_attempt (`key`);

CREATE INDEX ix_login_attempt_created_at ON login_attempt (created_at);


CREATE TABLE user (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	name VARCHAR(100) NOT NULL, 
	email VARCHAR(254) NOT NULL, 
	password_hash VARCHAR(255) NOT NULL, 
	`role` VARCHAR(20) NOT NULL, 
	department VARCHAR(100) NOT NULL, 
	active BOOL NOT NULL, 
	session_version INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (email)
)

;


CREATE TABLE ticket (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	title VARCHAR(180) NOT NULL, 
	description TEXT NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	priority VARCHAR(20) NOT NULL, 
	status VARCHAR(30) NOT NULL, 
	requester_id INTEGER NOT NULL, 
	assignee_id INTEGER, 
	created_at DATETIME NOT NULL, 
	updated_at DATETIME NOT NULL, 
	due_at DATETIME NOT NULL, 
	resolved_at DATETIME, 
	resolution TEXT NOT NULL, 
	version INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(requester_id) REFERENCES user (id), 
	FOREIGN KEY(assignee_id) REFERENCES user (id)
)

;

CREATE INDEX ix_ticket_due_at ON ticket (due_at);

CREATE INDEX ix_ticket_requester_id ON ticket (requester_id);

CREATE INDEX ix_ticket_assignee_id ON ticket (assignee_id);

CREATE INDEX ix_ticket_updated_at ON ticket (updated_at);


CREATE TABLE activity (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	actor_id INTEGER NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES ticket (id), 
	FOREIGN KEY(actor_id) REFERENCES user (id)
)

;

CREATE INDEX ix_activity_ticket_id ON activity (ticket_id);


CREATE TABLE attachment (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	uploader_id INTEGER NOT NULL, 
	filename VARCHAR(255) NOT NULL, 
	storage_name VARCHAR(100) NOT NULL, 
	size INTEGER NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES ticket (id), 
	FOREIGN KEY(uploader_id) REFERENCES user (id), 
	UNIQUE (storage_name)
)

;

CREATE INDEX ix_attachment_ticket_id ON attachment (ticket_id);


CREATE TABLE comment (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	ticket_id INTEGER NOT NULL, 
	author_id INTEGER NOT NULL, 
	body TEXT NOT NULL, 
	internal BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(ticket_id) REFERENCES ticket (id), 
	FOREIGN KEY(author_id) REFERENCES user (id)
)

;

CREATE INDEX ix_comment_ticket_id ON comment (ticket_id);


CREATE TABLE notification (
	id INTEGER NOT NULL AUTO_INCREMENT, 
	user_id INTEGER NOT NULL, 
	ticket_id INTEGER NOT NULL, 
	message VARCHAR(500) NOT NULL, 
	`read` BOOL NOT NULL, 
	created_at DATETIME NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(user_id) REFERENCES user (id), 
	FOREIGN KEY(ticket_id) REFERENCES ticket (id)
)

;

CREATE INDEX ix_notification_user_id ON notification (user_id);