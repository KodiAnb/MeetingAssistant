--CREATE DATABASE assistant;


--CREATE TABLE meeting (
  --  meeting_id SERIAL PRIMARY KEY,
  --  title TEXT,
  --  transcript TEXT
--);

    --INSERT INTO meetings (title, transcript) VALUES ('Recipe', 'createts');
--CREATE TABLE tasks(
 --  task_id int GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
 --  meeting_id int REFERENCES meetings(meeting_id),
 --  task_title TEXT,
 --  task TEXT
--);

--INSERT INTO tasks (meeting_id,task_title,task) VALUES (1, 'Do Work', 'Work on smt useful')

--SELECT *
--FROM tasks
--INNER JOIN meetings
--ON tasks.meeting_id = meetings.meeting_id;

--ALTER TABLE meeting DROP COLUMN calendar;


ALTER TABLE meeting ADD COLUMN miscellaneous JSONB;
--ALTER TABLE meeting ALTER COLUMN google_document TYPE JSONB USING to_jsonb(google_document);
