CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS properties (
  property_id TEXT PRIMARY KEY, area_sqm NUMERIC NOT NULL CHECK (area_sqm > 0), property_type TEXT NOT NULL,
  bedrooms INTEGER, location GEOGRAPHY(Point, 4326) NOT NULL
);
CREATE TABLE IF NOT EXISTS sales (
  sale_id TEXT PRIMARY KEY, property_id TEXT REFERENCES properties, sale_date DATE NOT NULL,
  price NUMERIC NOT NULL CHECK (price > 0), area_sqm NUMERIC NOT NULL CHECK (area_sqm > 0),
  property_type TEXT NOT NULL, bedrooms INTEGER, location GEOGRAPHY(Point, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS sales_location_gix ON sales USING GIST(location);
CREATE TABLE IF NOT EXISTS market_indices (index_date DATE PRIMARY KEY, value NUMERIC NOT NULL CHECK (value > 0));
