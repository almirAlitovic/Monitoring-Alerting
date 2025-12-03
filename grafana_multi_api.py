#!/usr/bin/env python3
"""
Multi-Source Data Collector for Grafana
Fetches data from APIs, PostgreSQL, and Elasticsearch and exposes metrics for Grafana
"""

import json
import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
import requests
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from elasticsearch import Elasticsearch

app = Flask(__name__)

# Configuration
API_SOURCES = {
    'weather': 'https://api.open-meteo.com/v1/forecast',
    'crypto': 'https://api.coingecko.com/api/v3/simple/price',
    'github': 'https://api.github.com/repos'
}

# ENV variables
PG_USER = os.getenv("PG_USER")
PG_PASSWORD = os.getenv("PG_PASSWORD")
ELASTIC_USER = os.getenv("ELASTIC_USER")
ELASTIC_PASS = os.getenv("ELASTIC_PASS")

# Database Configuration
POSTGRES_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'metrics_db',
    'user': PG_USER,
    'password': PG_PASSWORD
}

ELASTICSEARCH_CONFIG = {
    'hosts': ['http://localhost:9200'],
    'basic_auth': (ELASTIC_USER, ELASTIC_PASS)
}

class APIDataCollector:
    """Collects data from multiple APIs"""
    
    @staticmethod
    def fetch_weather_data(lat: float = 44.539051, lon: float = 18.477280) -> Dict:
        """Fetch weather data from Open-Meteo API"""
        try:
            params = {
                'latitude': lat,
                'longitude': lon,
                'current': 'temperature_2m,wind_speed_10m,relative_humidity_2m'
            }
            resp = requests.get(API_SOURCES['weather'], params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                'temperature': data['current']['temperature_2m'],
                'wind_speed': data['current']['wind_speed_10m'],
                'humidity': data['current']['relative_humidity_2m']
            }
        except Exception as e:
            print(f"Weather API error: {e}")
            return {}
    
    @staticmethod
    def fetch_crypto_prices(coins: List[str] = ['bitcoin', 'ethereum']) -> Dict:
        """Fetch cryptocurrency prices from CoinGecko API"""
        try:
            params = {
                'ids': ','.join(coins),
                'vs_currencies': 'usd'
            }
            resp = requests.get(API_SOURCES['crypto'], params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {coin: data[coin]['usd'] for coin in coins if coin in data}
        except Exception as e:
            print(f"Crypto API error: {e}")
            return {}
    
    @staticmethod
    def fetch_github_stats(repo: str = 'torvalds/linux') -> Dict:
        """Fetch GitHub repository statistics"""
        try:
            resp = requests.get(f"{API_SOURCES['github']}/{repo}", timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return {
                'stars': data['stargazers_count'],
                'forks': data['forks_count'],
                'open_issues': data['open_issues_count'],
                'watchers': data['watchers_count']
            }
        except Exception as e:
            print(f"GitHub API error: {e}")
            return {}


class PostgreSQLCollector:
    """Collects data from PostgreSQL database"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.conn = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            return True
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
    
    def fetch_metrics(self, query: str = None) -> List[Dict]:
        """Fetch metrics from PostgreSQL"""
        if not query:
            # Default query - assumes a metrics table exists
            query = """
                SELECT 
                    metric_name,
                    metric_value,
                    timestamp
                FROM metrics
                WHERE timestamp >= NOW() - INTERVAL '1 hour'
                ORDER BY timestamp DESC
            """
        
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"PostgreSQL query error: {e}")
            return []
    
    def fetch_aggregated_metrics(self) -> Dict:
        """Fetch aggregated metrics from PostgreSQL"""
        query = """
            SELECT 
                metric_name,
                AVG(metric_value) as avg_value,
                MAX(metric_value) as max_value,
                MIN(metric_value) as min_value,
                COUNT(*) as count
            FROM metrics
            WHERE timestamp >= NOW() - INTERVAL '24 hours'
            GROUP BY metric_name
        """
        
        try:
            results = self.fetch_metrics(query)
            return {row['metric_name']: row for row in results}
        except Exception as e:
            print(f"PostgreSQL aggregation error: {e}")
            return {}
    
    def fetch_time_series(self, metric_name: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch time series data for a specific metric"""
        query = """
            SELECT 
                timestamp,
                metric_value
            FROM metrics
            WHERE metric_name = %s
                AND timestamp >= %s
                AND timestamp <= %s
            ORDER BY timestamp ASC
        """
        
        try:
            if not self.conn or self.conn.closed:
                self.connect()
            
            with self.conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, (metric_name, start_time, end_time))
                results = cursor.fetchall()
                return [dict(row) for row in results]
        except Exception as e:
            print(f"PostgreSQL time series error: {e}")
            return []


class ElasticsearchCollector:
    """Collects data from Elasticsearch"""
    
    def __init__(self, config: Dict):
        try:
            self.es = Elasticsearch(**config)
            self.connected = self.es.ping()
        except Exception as e:
            print(f"Elasticsearch connection error: {e}")
            self.es = None
            self.connected = False
    
    def fetch_log_metrics(self, index: str = 'logs-*', time_field: str = '@timestamp') -> Dict:
        """Fetch log-based metrics from Elasticsearch"""
        if not self.connected:
            return {}
        
        try:
            # Query for log counts and error rates
            query = {
                "size": 0,
                "query": {
                    "range": {
                        time_field: {
                            "gte": "now-1h"
                        }
                    }
                },
                "aggs": {
                    "log_levels": {
                        "terms": {
                            "field": "level.keyword",
                            "size": 10
                        }
                    },
                    "error_count": {
                        "filter": {
                            "term": {
                                "level.keyword": "ERROR"
                            }
                        }
                    }
                }
            }
            
            result = self.es.search(index=index, body=query)
            
            metrics = {
                'total_logs': result['hits']['total']['value'],
                'error_count': result['aggregations']['error_count']['doc_count']
            }
            
            # Add log level counts
            for bucket in result['aggregations']['log_levels']['buckets']:
                metrics[f"logs_{bucket['key'].lower()}"] = bucket['doc_count']
            
            return metrics
        except Exception as e:
            print(f"Elasticsearch query error: {e}")
            return {}
    
    def fetch_time_series(self, index: str, metric_field: str, start_time: datetime, end_time: datetime) -> List[Dict]:
        """Fetch time series data from Elasticsearch"""
        if not self.connected:
            return []
        
        try:
            query = {
                "size": 0,
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": start_time.isoformat(),
                            "lte": end_time.isoformat()
                        }
                    }
                },
                "aggs": {
                    "time_buckets": {
                        "date_histogram": {
                            "field": "@timestamp",
                            "fixed_interval": "5m"
                        },
                        "aggs": {
                            "avg_value": {
                                "avg": {
                                    "field": metric_field
                                }
                            }
                        }
                    }
                }
            }
            
            result = self.es.search(index=index, body=query)
            
            time_series = []
            for bucket in result['aggregations']['time_buckets']['buckets']:
                time_series.append({
                    'timestamp': bucket['key'],
                    'value': bucket['avg_value']['value'] or 0
                })
            
            return time_series
        except Exception as e:
            print(f"Elasticsearch time series error: {e}")
            return []
    
    def fetch_application_metrics(self, index: str = 'metrics-*') -> Dict:
        """Fetch application performance metrics"""
        if not self.connected:
            return {}
        
        try:
            query = {
                "size": 0,
                "query": {
                    "range": {
                        "@timestamp": {
                            "gte": "now-5m"
                        }
                    }
                },
                "aggs": {
                    "avg_response_time": {
                        "avg": {
                            "field": "response_time"
                        }
                    },
                    "request_count": {
                        "value_count": {
                            "field": "request_id"
                        }
                    },
                    "status_codes": {
                        "terms": {
                            "field": "status_code",
                            "size": 10
                        }
                    }
                }
            }
            
            result = self.es.search(index=index, body=query)
            
            metrics = {
                'avg_response_time': result['aggregations']['avg_response_time']['value'] or 0,
                'request_count': result['aggregations']['request_count']['value']
            }
            
            for bucket in result['aggregations']['status_codes']['buckets']:
                metrics[f"status_{bucket['key']}"] = bucket['doc_count']
            
            return metrics
        except Exception as e:
            print(f"Elasticsearch application metrics error: {e}")
            return {}


# Initialize collectors
pg_collector = PostgreSQLCollector(POSTGRES_CONFIG)
es_collector = ElasticsearchCollector(ELASTICSEARCH_CONFIG)

# Grafana SimpleJson endpoints
@app.route('/')
def health():
    """Health check endpoint"""
    status = {
        'status': 'ok',
        'message': 'Multi-source data collector is running',
        'datasources': {
            'postgresql': pg_collector.connect(),
            'elasticsearch': es_collector.connected,
            'apis': True
        }
    }
    pg_collector.disconnect()
    return jsonify(status)

@app.route('/search', methods=['POST'])
def search():
    """Return available metrics"""
    metrics = [
        # API metrics
        'api.weather.temperature',
        'api.weather.wind_speed',
        'api.weather.humidity',
        'api.crypto.bitcoin',
        'api.crypto.ethereum',
        'api.github.stars',
        'api.github.forks',
        'api.github.open_issues',
        # PostgreSQL metrics
        'postgres.cpu_usage',
        'postgres.memory_usage',
        'postgres.disk_io',
        'postgres.connections',
        # Elasticsearch metrics
        'elastic.total_logs',
        'elastic.error_count',
        'elastic.avg_response_time',
        'elastic.request_count'
    ]
    return jsonify(metrics)

@app.route('/query', methods=['POST'])
def query():
    """Query endpoint for time series data"""
    req = request.get_json()
    
    api_collector = APIDataCollector()
    results = []
    
    # Parse time range
    time_from = datetime.fromisoformat(req['range']['from'].replace('Z', '+00:00'))
    time_to = datetime.fromisoformat(req['range']['to'].replace('Z', '+00:00'))
    
    # Generate timestamps
    timestamps = []
    current = time_from
    while current <= time_to:
        timestamps.append(int(current.timestamp() * 1000))
        current += timedelta(minutes=5)
    
    for target in req['targets']:
        metric = target['target']
        datapoints = []
        
        # API Data
        if metric.startswith('api.weather.'):
            weather_data = api_collector.fetch_weather_data()
            metric_name = metric.split('.')[-1]
            if metric_name in weather_data:
                value = weather_data[metric_name]
                for ts in timestamps:
                    datapoints.append([value + (hash(ts) % 10 - 5) * 0.1, ts])
        
        elif metric.startswith('api.crypto.'):
            crypto_data = api_collector.fetch_crypto_prices()
            coin = metric.split('.')[-1]
            if coin in crypto_data:
                value = crypto_data[coin]
                for ts in timestamps:
                    datapoints.append([value + (hash(ts) % 100 - 50), ts])
        
        elif metric.startswith('api.github.'):
            github_data = api_collector.fetch_github_stats()
            metric_name = metric.split('.')[-1]
            if metric_name in github_data:
                value = github_data[metric_name]
                for ts in timestamps:
                    datapoints.append([value + (hash(ts) % 20 - 10), ts])
        
        # PostgreSQL Data
        elif metric.startswith('postgres.'):
            metric_name = metric.split('.')[-1]
            pg_data = pg_collector.fetch_time_series(metric_name, time_from, time_to)
            for row in pg_data:
                ts = int(row['timestamp'].timestamp() * 1000)
                datapoints.append([float(row['metric_value']), ts])
        
        # Elasticsearch Data
        elif metric.startswith('elastic.'):
            metric_name = metric.split('.')[-1]
            es_data = es_collector.fetch_time_series('metrics-*', metric_name, time_from, time_to)
            for row in es_data:
                datapoints.append([float(row['value']), row['timestamp']])
        
        results.append({
            'target': metric,
            'datapoints': datapoints
        })
    
    return jsonify(results)

@app.route('/annotations', methods=['POST'])
def annotations():
    """Annotations endpoint"""
    return jsonify([])

# Standalone data collection script
def collect_and_display():
    """Collect data from all sources and display"""
    api_collector = APIDataCollector()
    
    print("=" * 60)
    print("Multi-Source Data Collection for Grafana")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    # API Data
    print(" API Data:")
    print("\n  Weather Data (Lukavac):")
    weather = api_collector.fetch_weather_data()
    for key, value in weather.items():
        print(f"    {key}: {value}")
    
    print("\n Cryptocurrency Prices:")
    crypto = api_collector.fetch_crypto_prices()
    for coin, price in crypto.items():
        print(f"    {coin}: ${price:,.2f}")
    
    print("\n GitHub Stats (torvalds/linux):")
    github = api_collector.fetch_github_stats()
    for key, value in github.items():
        print(f"    {key}: {value:,}")
    
    # PostgreSQL Data
    print("\n\n PostgreSQL Metrics:")
    pg_metrics = pg_collector.fetch_aggregated_metrics()
    if pg_metrics:
        for metric, values in pg_metrics.items():
            print(f"  {metric}:")
            print(f"    avg: {values.get('avg_value', 0):.2f}")
            print(f"    max: {values.get('max_value', 0):.2f}")
            print(f"    min: {values.get('min_value', 0):.2f}")
    else:
        print("No PostgreSQL connection or data available!")
    
    # Elasticsearch Data
    print("\n🔍 Elasticsearch Metrics:")
    es_logs = es_collector.fetch_log_metrics()
    if es_logs:
        for key, value in es_logs.items():
            print(f"  {key}: {value}")
    else:
        print("No Elasticsearch connection or data available!")
    
    es_app_metrics = es_collector.fetch_application_metrics()
    if es_app_metrics:
        print("\n  Application Metrics:")
        for key, value in es_app_metrics.items():
            print(f"    {key}: {value}")
    
    print("\n" + "=" * 60)
    
    return {
        'api': {
            'weather': weather,
            'crypto': crypto,
            'github': github
        },
        'postgresql': pg_metrics,
        'elasticsearch': {
            'logs': es_logs,
            'application': es_app_metrics
        },
        'timestamp': datetime.now().isoformat()
    }

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'collect':
        # Run as standalone collector
        data = collect_and_display()
        
        # Save to JSON file
        with open('multi_source_data.json', 'w') as f:
            json.dump(data, f, indent=2)
        print("\n Data saved to multi_source_data.json")
        
        # Cleanup
        pg_collector.disconnect()
    else:
        # Run as Flask server for Grafana
        print("Starting Multi-Source Grafana API server...")
        print("Server will be available at http://localhost:5000")
        print("\nData Sources:")
        print("  ✓ External APIs (Weather, Crypto, GitHub)")
        print("  ✓ PostgreSQL Database")
        print("  ✓ Elasticsearch")
        print("\nAvailable endpoints:")
        print("  GET  /        - Health check")
        print("  POST /search  - Get available metrics")
        print("  POST /query   - Query time series data")
        print("\nTo collect data once: python script.py collect")
        
        try:
            app.run(host='0.0.0.0', port=5000, debug=True)
        finally:
            pg_collector.disconnect()
