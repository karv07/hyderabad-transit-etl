"""
Hyderabad Transit Data ETL Pipeline
====================================
Real-time transit data extraction, transformation, and loading system
Author: Your Name
Date: 2026-03-17

Features:
- Extract live transit data from GTFS feeds and APIs
- Transform data for delay predictions and route optimization
- Load into PostgreSQL/BigQuery for analytics
- Generate insights on route efficiency and delays
"""

import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import time
from typing import Dict, List, Tuple
import sqlite3
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transit_etl.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class TransitDataExtractor:
    """Extract transit data from various sources"""
    
    def __init__(self, api_base_url: str = None):
        self.api_base_url = api_base_url or "https://api.transitland.org/v1"
        self.session = requests.Session()
        
    def extract_gtfs_routes(self, feed_id: str = "hyderabad") -> pd.DataFrame:
        """
        Extract route information from GTFS feed
        
        Simulates real API call with synthetic data for demo
        In production, this would call actual TGSRTC API
        """
        logger.info("Extracting GTFS route data...")
        
        # Simulate GTFS data (replace with actual API call in production)
        base_route_names = [
            'Secunderabad-Gachibowli', 'JNTU-Miyapur', 'Ameerpet-Lingampally',
            'LB Nagar-Dilsukhnagar', 'Kukatpally-KPHB', 'Madhapur-Hitech City',
            'Uppal-Habsiguda', 'Kompally-Alwal', 'Mehdipatnam-Tolichowki',
            'Charminar-Falaknuma', 'Paradise-Rasoolpura', 'AS Rao Nagar-Sainikpuri',
            'Kondapur-Manikonda', 'Shamshabad-Airport', 'Patancheru-Sangareddy',
            'Jubilee Hills-Banjara Hills', 'Begumpet-Somajiguda', 'Afzalgunj-Charminar',
            'Malakpet-Chaderghat', 'Tarnaka-Mettuguda', 'Nagole-Uppal', 'Koti-Abids',
            'Lakdikapul-Khairatabad', 'Nampally-Bahadurpura', 'Vanasthalipuram-LB Nagar'
        ]
        
        # Generate 50 routes
        route_names = []
        for i in range(50):
            route_names.append(base_route_names[i % len(base_route_names)])
        
        routes_data = {
            'route_id': [f'RT{i:03d}' for i in range(1, 51)],
            'route_name': route_names,
            'route_type': np.random.choice(['Express', 'Ordinary', 'Metro Express', 'City Bus'], 50),
            'total_stops': np.random.randint(8, 45, 50),
            'avg_trip_duration_min': np.random.randint(25, 120, 50),
            'frequency_per_hour': np.random.randint(2, 12, 50),
            'fare_min': np.random.randint(10, 25, 50),
            'fare_max': np.random.randint(30, 100, 50)
        }
        
        df = pd.DataFrame(routes_data)
        logger.info(f"Extracted {len(df)} routes")
        return df
    
    def extract_realtime_vehicle_positions(self) -> pd.DataFrame:
        """Extract real-time vehicle position data"""
        logger.info("Extracting real-time vehicle positions...")
        
        # Simulate real-time vehicle data
        num_vehicles = 500
        current_time = datetime.now()
        
        vehicle_data = {
            'vehicle_id': [f'BUS{i:04d}' for i in range(1, num_vehicles + 1)],
            'route_id': [f'RT{np.random.randint(1, 51):03d}' for _ in range(num_vehicles)],
            'latitude': np.random.uniform(17.3850, 17.5350, num_vehicles),  # Hyderabad coords
            'longitude': np.random.uniform(78.4000, 78.5500, num_vehicles),
            'speed_kmh': np.random.uniform(0, 60, num_vehicles),
            'timestamp': [current_time - timedelta(seconds=np.random.randint(0, 300)) 
                         for _ in range(num_vehicles)],
            'occupancy_percent': np.random.randint(20, 100, num_vehicles),
            'next_stop_eta_min': np.random.randint(1, 15, num_vehicles),
            'delay_minutes': np.random.randint(-5, 30, num_vehicles)  # Negative = early
        }
        
        df = pd.DataFrame(vehicle_data)
        logger.info(f"Extracted {len(df)} vehicle positions")
        return df
    
    def extract_historical_delays(self, days_back: int = 30) -> pd.DataFrame:
        """Extract historical delay data for pattern analysis"""
        logger.info(f"Extracting {days_back} days of historical delay data...")
        
        # Generate synthetic historical data
        records = []
        end_date = datetime.now()
        
        for day in range(days_back):
            current_date = end_date - timedelta(days=day)
            
            # More records for recent days
            num_records = np.random.randint(800, 1200)
            
            for _ in range(num_records):
                hour = np.random.randint(6, 23)  # 6 AM to 11 PM
                
                # Peak hours have more delays
                if hour in [8, 9, 17, 18, 19]:  # Morning and evening rush
                    delay = np.random.gamma(4, 3)  # More delays in peak hours
                else:
                    delay = np.random.gamma(2, 2)
                
                records.append({
                    'date': current_date.date(),
                    'hour': hour,
                    'route_id': f'RT{np.random.randint(1, 51):03d}',
                    'vehicle_id': f'BUS{np.random.randint(1, 501):04d}',
                    'scheduled_time': f'{hour:02d}:{np.random.randint(0, 60):02d}',
                    'actual_arrival_delay_min': delay,
                    'weather_condition': np.random.choice(
                        ['Clear', 'Rain', 'Heavy Rain', 'Cloudy'], 
                        p=[0.6, 0.2, 0.1, 0.1]
                    ),
                    'is_weekend': current_date.weekday() >= 5,
                    'passenger_load': np.random.randint(10, 100)
                })
        
        df = pd.DataFrame(records)
        logger.info(f"Extracted {len(df)} historical delay records")
        return df


class TransitDataTransformer:
    """Transform and enrich transit data"""
    
    @staticmethod
    def calculate_delay_metrics(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate various delay metrics and statistics"""
        logger.info("Calculating delay metrics...")
        
        # Group by route and calculate metrics
        delay_metrics = df.groupby('route_id').agg({
            'actual_arrival_delay_min': ['mean', 'median', 'std', 'max', 'count']
        }).round(2)
        
        delay_metrics.columns = ['avg_delay', 'median_delay', 'delay_std', 
                                 'max_delay', 'total_trips']
        delay_metrics = delay_metrics.reset_index()
        
        # Calculate reliability score (0-100)
        delay_metrics['reliability_score'] = (
            100 - (delay_metrics['avg_delay'] * 2)
        ).clip(0, 100).round(1)
        
        # Categorize routes
        delay_metrics['performance_category'] = pd.cut(
            delay_metrics['avg_delay'],
            bins=[-np.inf, 3, 7, 15, np.inf],
            labels=['Excellent', 'Good', 'Fair', 'Poor']
        )
        
        logger.info(f"Calculated metrics for {len(delay_metrics)} routes")
        return delay_metrics
    
    @staticmethod
    def identify_peak_delay_patterns(df: pd.DataFrame) -> pd.DataFrame:
        """Identify patterns in delays by time of day"""
        logger.info("Identifying peak delay patterns...")
        
        hourly_delays = df.groupby('hour').agg({
            'actual_arrival_delay_min': ['mean', 'count']
        }).round(2)
        
        hourly_delays.columns = ['avg_delay', 'num_trips']
        hourly_delays = hourly_delays.reset_index()
        
        # Categorize hours
        hourly_delays['period'] = hourly_delays['hour'].apply(
            lambda x: 'Morning Peak' if x in [7, 8, 9] 
            else 'Evening Peak' if x in [17, 18, 19] 
            else 'Off Peak'
        )
        
        return hourly_delays
    
    @staticmethod
    def analyze_weather_impact(df: pd.DataFrame) -> pd.DataFrame:
        """Analyze impact of weather on delays"""
        logger.info("Analyzing weather impact on delays...")
        
        weather_analysis = df.groupby('weather_condition').agg({
            'actual_arrival_delay_min': ['mean', 'median', 'count']
        }).round(2)
        
        weather_analysis.columns = ['avg_delay', 'median_delay', 'num_trips']
        weather_analysis = weather_analysis.reset_index()
        
        # Calculate delay increase vs clear weather
        baseline_delay = weather_analysis[
            weather_analysis['weather_condition'] == 'Clear'
        ]['avg_delay'].values[0]
        
        weather_analysis['delay_increase_pct'] = (
            ((weather_analysis['avg_delay'] - baseline_delay) / baseline_delay) * 100
        ).round(1)
        
        return weather_analysis
    
    @staticmethod
    def optimize_route_efficiency(routes_df: pd.DataFrame, 
                                  delays_df: pd.DataFrame) -> pd.DataFrame:
        """Calculate route efficiency and optimization recommendations"""
        logger.info("Optimizing route efficiency...")
        
        # Merge route info with delay metrics
        route_delays = delays_df.groupby('route_id').agg({
            'actual_arrival_delay_min': 'mean'
        }).round(2)
        
        if 'route_id' not in routes_df.columns:
            return pd.DataFrame()
        
        optimized = routes_df.merge(route_delays, on='route_id', how='left')
        optimized.columns = list(routes_df.columns) + ['avg_delay']
        
        # Calculate efficiency score
        optimized['efficiency_score'] = (
            (optimized['frequency_per_hour'] * 10) - 
            (optimized['avg_delay'].fillna(0) * 2)
        ).clip(0, 100).round(1)
        
        # Generate recommendations
        optimized['recommendation'] = optimized.apply(
            lambda row: 'Increase frequency' if row['avg_delay'] > 10 and row['frequency_per_hour'] < 6
            else 'Add express service' if row['avg_trip_duration_min'] > 60
            else 'Maintain current service' if row['efficiency_score'] > 70
            else 'Review route alignment',
            axis=1
        )
        
        return optimized


class TransitDataLoader:
    """Load transformed data into database"""
    
    def __init__(self, db_path: str = 'transit_data.db'):
        self.db_path = db_path
        self.conn = None
        
    def connect(self):
        """Establish database connection"""
        self.conn = sqlite3.connect(self.db_path)
        logger.info(f"Connected to database: {self.db_path}")
        
    def load_to_db(self, df: pd.DataFrame, table_name: str, 
                   if_exists: str = 'replace'):
        """Load dataframe to database table"""
        if self.conn is None:
            self.connect()
            
        df.to_sql(table_name, self.conn, if_exists=if_exists, index=False)
        logger.info(f"Loaded {len(df)} records to {table_name}")
        
    def execute_query(self, query: str) -> pd.DataFrame:
        """Execute SQL query and return results"""
        if self.conn is None:
            self.connect()
            
        return pd.read_sql_query(query, self.conn)
    
    def generate_summary_statistics(self) -> Dict:
        """Generate summary statistics from loaded data"""
        stats = {
            'total_routes': self.execute_query(
                "SELECT COUNT(DISTINCT route_id) as count FROM route_delays"
            )['count'].values[0],
            'total_vehicles': self.execute_query(
                "SELECT COUNT(DISTINCT vehicle_id) as count FROM vehicle_positions"
            )['count'].values[0],
            'avg_system_delay': self.execute_query(
                "SELECT AVG(avg_delay) as avg FROM route_delays"
            )['avg'].values[0],
            'total_trips_analyzed': self.execute_query(
                "SELECT SUM(total_trips) as total FROM route_delays"
            )['total'].values[0]
        }
        
        return stats
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")


class TransitETLPipeline:
    """Main ETL pipeline orchestrator"""
    
    def __init__(self):
        self.extractor = TransitDataExtractor()
        self.transformer = TransitDataTransformer()
        self.loader = TransitDataLoader()
        
    def run_full_pipeline(self, historical_days: int = 30) -> Dict:
        """Execute complete ETL pipeline"""
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("Starting Transit Data ETL Pipeline")
        logger.info("=" * 60)
        
        # EXTRACT
        logger.info("\n[EXTRACT PHASE]")
        routes_df = self.extractor.extract_gtfs_routes()
        vehicles_df = self.extractor.extract_realtime_vehicle_positions()
        delays_df = self.extractor.extract_historical_delays(historical_days)
        
        # TRANSFORM
        logger.info("\n[TRANSFORM PHASE]")
        delay_metrics = self.transformer.calculate_delay_metrics(delays_df)
        hourly_patterns = self.transformer.identify_peak_delay_patterns(delays_df)
        weather_impact = self.transformer.analyze_weather_impact(delays_df)
        optimized_routes = self.transformer.optimize_route_efficiency(routes_df, delays_df)
        
        # LOAD
        logger.info("\n[LOAD PHASE]")
        self.loader.connect()
        self.loader.load_to_db(routes_df, 'routes')
        self.loader.load_to_db(vehicles_df, 'vehicle_positions')
        self.loader.load_to_db(delays_df, 'historical_delays')
        self.loader.load_to_db(delay_metrics, 'route_delays')
        self.loader.load_to_db(hourly_patterns, 'hourly_patterns')
        self.loader.load_to_db(weather_impact, 'weather_impact')
        self.loader.load_to_db(optimized_routes, 'route_optimization')
        
        # Generate summary
        summary = self.loader.generate_summary_statistics()
        
        elapsed_time = time.time() - start_time
        
        logger.info("\n[PIPELINE SUMMARY]")
        logger.info(f"Total Routes: {summary['total_routes']}")
        logger.info(f"Total Vehicles: {summary['total_vehicles']}")
        logger.info(f"Avg System Delay: {summary['avg_system_delay']:.2f} minutes")
        logger.info(f"Total Trips Analyzed: {summary['total_trips_analyzed']:,}")
        logger.info(f"Pipeline Execution Time: {elapsed_time:.2f} seconds")
        logger.info("=" * 60)
        
        self.loader.close()
        
        return {
            'status': 'success',
            'execution_time': elapsed_time,
            'summary': summary,
            'records_processed': len(delays_df)
        }
    
    def run_incremental_update(self):
        """Run incremental update for real-time data"""
        logger.info("Running incremental update...")
        
        vehicles_df = self.extractor.extract_realtime_vehicle_positions()
        self.loader.connect()
        self.loader.load_to_db(vehicles_df, 'vehicle_positions', if_exists='replace')
        
        logger.info("Incremental update complete")
        self.loader.close()


if __name__ == "__main__":
    # Run the ETL pipeline
    pipeline = TransitETLPipeline()
    result = pipeline.run_full_pipeline(historical_days=30)
    
    print("\n✅ ETL Pipeline completed successfully!")
    print(f"📊 Processed {result['records_processed']:,} records in {result['execution_time']:.2f}s")
    print(f"🚌 System Average Delay: {result['summary']['avg_system_delay']:.2f} minutes")
    print(f"📁 Data saved to: transit_data.db")
