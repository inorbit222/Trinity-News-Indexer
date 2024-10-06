--
-- PostgreSQL database dump
--

-- Dumped from database version 16.4
-- Dumped by pg_dump version 16.4

-- Started on 2024-10-06 16:07:18

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 223 (class 1259 OID 43833)
-- Name: article_topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.article_topics (
    article_id integer NOT NULL,
    topic_id integer NOT NULL,
    topic_weight real
);


ALTER TABLE public.article_topics OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 43794)
-- Name: articles; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.articles (
    article_id integer NOT NULL,
    newspaper_id integer,
    title character varying(255),
    content text,
    embedding_vector bytea,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    embedding_vector_binary bytea,
    embedding_vector_array numeric[],
    named_entities jsonb,
    lda_topics jsonb
);


ALTER TABLE public.articles OWNER TO postgres;

--
-- TOC entry 217 (class 1259 OID 43793)
-- Name: articles_article_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.articles_article_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.articles_article_id_seq OWNER TO postgres;

--
-- TOC entry 4850 (class 0 OID 0)
-- Dependencies: 217
-- Name: articles_article_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.articles_article_id_seq OWNED BY public.articles.article_id;


--
-- TOC entry 220 (class 1259 OID 43810)
-- Name: entities; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.entities (
    entity_id integer NOT NULL,
    article_id integer,
    entity_type character varying(255),
    entity_value character varying(255),
    start_pos integer,
    end_pos integer,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.entities OWNER TO postgres;

--
-- TOC entry 219 (class 1259 OID 43809)
-- Name: entities_entity_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.entities_entity_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.entities_entity_id_seq OWNER TO postgres;

--
-- TOC entry 4851 (class 0 OID 0)
-- Dependencies: 219
-- Name: entities_entity_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.entities_entity_id_seq OWNED BY public.entities.entity_id;


--
-- TOC entry 226 (class 1259 OID 43860)
-- Name: entity_sentiments; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.entity_sentiments (
    id integer NOT NULL,
    entity_id integer,
    sentiment_pos double precision,
    sentiment_neg double precision,
    sentiment_neu double precision,
    sentiment_compound double precision
);


ALTER TABLE public.entity_sentiments OWNER TO postgres;

--
-- TOC entry 225 (class 1259 OID 43859)
-- Name: entity_sentiments_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.entity_sentiments_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.entity_sentiments_id_seq OWNER TO postgres;

--
-- TOC entry 4852 (class 0 OID 0)
-- Dependencies: 225
-- Name: entity_sentiments_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.entity_sentiments_id_seq OWNED BY public.entity_sentiments.id;


--
-- TOC entry 228 (class 1259 OID 43872)
-- Name: faiss_index; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.faiss_index (
    index_id integer NOT NULL,
    article_id integer,
    faiss_vector bytea
);


ALTER TABLE public.faiss_index OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 43871)
-- Name: faiss_index_index_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.faiss_index_index_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.faiss_index_index_id_seq OWNER TO postgres;

--
-- TOC entry 4853 (class 0 OID 0)
-- Dependencies: 227
-- Name: faiss_index_index_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.faiss_index_index_id_seq OWNED BY public.faiss_index.index_id;


--
-- TOC entry 224 (class 1259 OID 43848)
-- Name: geocoded_locations; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.geocoded_locations (
    entity_id integer NOT NULL,
    latitude numeric(9,6),
    longitude numeric(9,6),
    geocoding_source character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


ALTER TABLE public.geocoded_locations OWNER TO postgres;

--
-- TOC entry 216 (class 1259 OID 43783)
-- Name: newspapers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.newspapers (
    newspaper_id integer NOT NULL,
    title character varying(255) NOT NULL,
    publication_date date NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    toc text,
    hyperlink text
);


ALTER TABLE public.newspapers OWNER TO postgres;

--
-- TOC entry 215 (class 1259 OID 43782)
-- Name: newspapers_newspaper_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.newspapers_newspaper_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.newspapers_newspaper_id_seq OWNER TO postgres;

--
-- TOC entry 4854 (class 0 OID 0)
-- Dependencies: 215
-- Name: newspapers_newspaper_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.newspapers_newspaper_id_seq OWNED BY public.newspapers.newspaper_id;


--
-- TOC entry 222 (class 1259 OID 43825)
-- Name: topics; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.topics (
    topic_id integer NOT NULL,
    topic_name character varying(100) NOT NULL,
    description text,
    article_id integer,
    topic_weight text
);


ALTER TABLE public.topics OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 43824)
-- Name: topics_topic_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.topics_topic_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.topics_topic_id_seq OWNER TO postgres;

--
-- TOC entry 4855 (class 0 OID 0)
-- Dependencies: 221
-- Name: topics_topic_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.topics_topic_id_seq OWNED BY public.topics.topic_id;


--
-- TOC entry 4670 (class 2604 OID 43797)
-- Name: articles article_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.articles ALTER COLUMN article_id SET DEFAULT nextval('public.articles_article_id_seq'::regclass);


--
-- TOC entry 4673 (class 2604 OID 43813)
-- Name: entities entity_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entities ALTER COLUMN entity_id SET DEFAULT nextval('public.entities_entity_id_seq'::regclass);


--
-- TOC entry 4677 (class 2604 OID 43863)
-- Name: entity_sentiments id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_sentiments ALTER COLUMN id SET DEFAULT nextval('public.entity_sentiments_id_seq'::regclass);


--
-- TOC entry 4678 (class 2604 OID 43875)
-- Name: faiss_index index_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.faiss_index ALTER COLUMN index_id SET DEFAULT nextval('public.faiss_index_index_id_seq'::regclass);


--
-- TOC entry 4667 (class 2604 OID 43786)
-- Name: newspapers newspaper_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.newspapers ALTER COLUMN newspaper_id SET DEFAULT nextval('public.newspapers_newspaper_id_seq'::regclass);


--
-- TOC entry 4675 (class 2604 OID 43828)
-- Name: topics topic_id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics ALTER COLUMN topic_id SET DEFAULT nextval('public.topics_topic_id_seq'::regclass);


--
-- TOC entry 4688 (class 2606 OID 43837)
-- Name: article_topics article_topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.article_topics
    ADD CONSTRAINT article_topics_pkey PRIMARY KEY (article_id, topic_id);


--
-- TOC entry 4682 (class 2606 OID 43803)
-- Name: articles articles_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_pkey PRIMARY KEY (article_id);


--
-- TOC entry 4684 (class 2606 OID 43818)
-- Name: entities entities_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_pkey PRIMARY KEY (entity_id);


--
-- TOC entry 4692 (class 2606 OID 43865)
-- Name: entity_sentiments entity_sentiments_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_sentiments
    ADD CONSTRAINT entity_sentiments_pkey PRIMARY KEY (id);


--
-- TOC entry 4694 (class 2606 OID 43879)
-- Name: faiss_index faiss_index_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.faiss_index
    ADD CONSTRAINT faiss_index_pkey PRIMARY KEY (index_id);


--
-- TOC entry 4690 (class 2606 OID 43853)
-- Name: geocoded_locations geocoded_locations_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geocoded_locations
    ADD CONSTRAINT geocoded_locations_pkey PRIMARY KEY (entity_id);


--
-- TOC entry 4680 (class 2606 OID 43792)
-- Name: newspapers newspapers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.newspapers
    ADD CONSTRAINT newspapers_pkey PRIMARY KEY (newspaper_id);


--
-- TOC entry 4686 (class 2606 OID 43832)
-- Name: topics topics_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.topics
    ADD CONSTRAINT topics_pkey PRIMARY KEY (topic_id);


--
-- TOC entry 4697 (class 2606 OID 43838)
-- Name: article_topics article_topics_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.article_topics
    ADD CONSTRAINT article_topics_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(article_id);


--
-- TOC entry 4698 (class 2606 OID 43843)
-- Name: article_topics article_topics_topic_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.article_topics
    ADD CONSTRAINT article_topics_topic_id_fkey FOREIGN KEY (topic_id) REFERENCES public.topics(topic_id);


--
-- TOC entry 4695 (class 2606 OID 43804)
-- Name: articles articles_newspaper_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.articles
    ADD CONSTRAINT articles_newspaper_id_fkey FOREIGN KEY (newspaper_id) REFERENCES public.newspapers(newspaper_id);


--
-- TOC entry 4696 (class 2606 OID 43819)
-- Name: entities entities_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entities
    ADD CONSTRAINT entities_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(article_id);


--
-- TOC entry 4700 (class 2606 OID 43866)
-- Name: entity_sentiments entity_sentiments_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.entity_sentiments
    ADD CONSTRAINT entity_sentiments_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES public.entities(entity_id);


--
-- TOC entry 4701 (class 2606 OID 43880)
-- Name: faiss_index faiss_index_article_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.faiss_index
    ADD CONSTRAINT faiss_index_article_id_fkey FOREIGN KEY (article_id) REFERENCES public.articles(article_id);


--
-- TOC entry 4699 (class 2606 OID 43854)
-- Name: geocoded_locations geocoded_locations_entity_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.geocoded_locations
    ADD CONSTRAINT geocoded_locations_entity_id_fkey FOREIGN KEY (entity_id) REFERENCES public.entities(entity_id);


-- Completed on 2024-10-06 16:07:18

--
-- PostgreSQL database dump complete
--

