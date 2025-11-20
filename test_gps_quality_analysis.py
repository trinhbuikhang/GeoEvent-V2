#!/usr/bin/env python3
"""
GPS Quality Analysis Tool for GeoEvent Application

This tool performs comprehensive analysis of GPS data quality in test folders,
particularly focusing on corrupted or problematic GPS data that can cause
application freezes or rendering issues.

Usage:
    python test_gps_quality_analysis.py [folder_path]

If no folder_path is provided, it analyzes all folders in testdata/err/
"""

import os
import sys
import csv
import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class GPSPoint:
    """Represents a single GPS data point"""
    timestamp: datetime
    chainage: float
    latitude: float
    longitude: float
    raw_row: List[str]

@dataclass
class GPSQualityMetrics:
    """Comprehensive GPS quality metrics"""
    total_points: int = 0
    valid_points: int = 0
    invalid_points: int = 0
    skipped_rows: int = 0  # Rows skipped during parsing

    # Chainage issues
    chainage_negative: int = 0
    chainage_too_large: int = 0  # > 10,000 km
    chainage_nan: int = 0
    chainage_infinite: int = 0
    chainage_non_monotonic: int = 0

    # Timestamp issues
    timestamp_invalid: int = 0
    timestamp_out_of_order: int = 0
    timestamp_missing: int = 0

    # Coordinate issues
    coord_invalid: int = 0
    coord_out_of_bounds: int = 0
    coord_missing: int = 0

    # Speed and movement analysis
    avg_speed_kmh: float = 0.0
    max_speed_kmh: float = 0.0
    min_speed_kmh: float = 0.0
    speed_spikes: int = 0  # Points with unrealistic speed changes

    # Time gaps
    time_gaps_count: int = 0
    max_time_gap_seconds: float = 0.0
    avg_time_gap_seconds: float = 0.0

    # Data density
    avg_distance_between_points: float = 0.0
    max_distance_between_points: float = 0.0

    # Data patterns
    duplicate_timestamps: int = 0
    duplicate_coordinates: int = 0
    data_gaps_large: int = 0  # Gaps > 10 minutes

    # Quality score (0-100)
    quality_score: float = 0.0
    risk_level: str = "Low"  # Low, Medium, High, Critical

class GPSQualityAnalyzer:
    """Advanced GPS quality analysis tool"""

    def __init__(self, base_path: str = None):
        if base_path is None:
            # Default to the err folder
            script_dir = Path(__file__).parent
            self.base_path = script_dir / "testdata" / "err"
        else:
            self.base_path = Path(base_path)

        self.results: Dict[str, GPSQualityMetrics] = {}

    def analyze_all_folders(self) -> Dict[str, GPSQualityMetrics]:
        """Analyze GPS quality for all folders in the base path"""
        if not self.base_path.exists():
            logger.error(f"Base path does not exist: {self.base_path}")
            return {}

        folders = [f for f in self.base_path.iterdir() if f.is_dir()]
        logger.info(f"Found {len(folders)} folders to analyze")

        for folder in folders:
            logger.info(f"Analyzing folder: {folder.name}")
            try:
                metrics = self.analyze_folder(folder)
                self.results[folder.name] = metrics
            except Exception as e:
                logger.error(f"Error analyzing folder {folder.name}: {e}")
                continue

        return self.results

    def analyze_folder(self, folder_path: Path) -> GPSQualityMetrics:
        """Analyze GPS quality for a single folder"""
        metrics = GPSQualityMetrics()

        # Find GPS file (.driveiri)
        gps_file = None
        for file in folder_path.glob("*.driveiri"):
            gps_file = file
            break

        if not gps_file:
            logger.warning(f"No .driveiri file found in {folder_path}")
            return metrics

        # Parse GPS data
        gps_points, skipped_count = self._parse_driveiri_file(gps_file)
        metrics.total_points = len(gps_points)
        metrics.skipped_rows = skipped_count

        if not gps_points:
            logger.warning(f"No GPS points found in {gps_file}")
            return metrics

        # Analyze each point
        valid_points = []
        prev_point = None
        timestamps_seen = set()
        coords_seen = set()

        for i, point in enumerate(gps_points):
            is_valid = self._analyze_point(point, metrics, prev_point, i, timestamps_seen, coords_seen)
            if is_valid:
                valid_points.append(point)
            prev_point = point

        metrics.valid_points = len(valid_points)
        metrics.invalid_points = metrics.total_points - metrics.valid_points

        # Calculate derived metrics
        if valid_points:
            self._calculate_derived_metrics(valid_points, metrics)

        # Calculate quality score and risk level
        metrics.quality_score = self._calculate_quality_score(metrics)
        metrics.risk_level = self._calculate_risk_level(metrics)

        return metrics

    def _parse_driveiri_file(self, file_path: Path) -> Tuple[List[GPSPoint], int]:
        """Parse .driveiri file and extract GPS points"""
        gps_points = []
        skipped_rows = 0

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                header = next(reader, None)  # Skip header row

                for row_num, row in enumerate(reader, 2):  # Start from row 2
                    if len(row) < 12:  # Need at least 12 columns
                        skipped_rows += 1
                        continue

                    try:
                        # Parse timestamp (column 3: GPSDateTime)
                        timestamp_str = row[2].strip()
                        if not timestamp_str:
                            skipped_rows += 1
                            continue  # Skip rows without timestamp

                        # Parse timestamp - handle different formats
                        try:
                            # Try MM/DD/YYYY format first
                            timestamp = datetime.strptime(timestamp_str, '%m/%d/%Y %I:%M:%S %p')
                        except ValueError:
                            try:
                                # Try ISO format
                                timestamp = datetime.fromisoformat(timestamp_str.replace(' ', 'T'))
                            except ValueError:
                                skipped_rows += 1
                                continue  # Skip invalid timestamps

                        # Parse chainage - use StartChainage (column 10)
                        chainage_str = row[10].strip()
                        if not chainage_str:
                            skipped_rows += 1
                            continue
                        chainage = float(chainage_str)

                        # Parse coordinates (columns 7-8: LAT, LON)
                        lat_str = row[7].strip()
                        lon_str = row[8].strip()
                        if not lat_str or not lon_str:
                            skipped_rows += 1
                            continue

                        lat = float(lat_str)
                        lon = float(lon_str)

                        point = GPSPoint(timestamp, chainage, lat, lon, row)
                        gps_points.append(point)

                    except (ValueError, IndexError) as e:
                        skipped_rows += 1
                        logger.debug(f"Skipping invalid row {row_num}: {e}")
                        continue

        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")

        return gps_points, skipped_rows

    def _analyze_point(self, point: GPSPoint, metrics: GPSQualityMetrics,
                      prev_point: Optional[GPSPoint], index: int,
                      timestamps_seen: set, coords_seen: set) -> bool:
        """Analyze a single GPS point and update metrics"""
        is_valid = True

        # Check for duplicate timestamps
        timestamp_key = point.timestamp.isoformat()
        if timestamp_key in timestamps_seen:
            metrics.duplicate_timestamps += 1
        else:
            timestamps_seen.add(timestamp_key)

        # Check for duplicate coordinates
        coord_key = ".6f"
        if coord_key in coords_seen:
            metrics.duplicate_coordinates += 1
        else:
            coords_seen.add(coord_key)

        # Check chainage validity
        if math.isnan(point.chainage) or math.isinf(point.chainage):
            metrics.chainage_nan += 1
            metrics.chainage_infinite += 1
            is_valid = False
        elif point.chainage < 0:
            metrics.chainage_negative += 1
            is_valid = False
        elif point.chainage > 10000:  # 10,000 km max
            metrics.chainage_too_large += 1
            is_valid = False

        # Check monotonic chainage
        if prev_point and point.chainage < prev_point.chainage:
            metrics.chainage_non_monotonic += 1
            is_valid = False

        # Check coordinates
        if not (-90 <= point.latitude <= 90) or not (-180 <= point.longitude <= 180):
            metrics.coord_out_of_bounds += 1
            is_valid = False

        if math.isnan(point.latitude) or math.isnan(point.longitude) or \
           math.isinf(point.latitude) or math.isinf(point.longitude):
            metrics.coord_invalid += 1
            is_valid = False

        # Check timestamp validity
        if point.timestamp.year < 2000 or point.timestamp.year > 2030:
            metrics.timestamp_invalid += 1
            is_valid = False

        # Check timestamp order
        if prev_point and point.timestamp < prev_point.timestamp:
            metrics.timestamp_out_of_order += 1
            is_valid = False

        return is_valid

    def _calculate_derived_metrics(self, valid_points: List[GPSPoint],
                                  metrics: GPSQualityMetrics):
        """Calculate derived metrics from valid GPS points"""
        if len(valid_points) < 2:
            return

        # Calculate speeds and time gaps
        speeds = []
        time_gaps = []
        distances = []

        for i in range(1, len(valid_points)):
            curr = valid_points[i]
            prev = valid_points[i-1]

            # Time gap in seconds
            time_gap = (curr.timestamp - prev.timestamp).total_seconds()
            if time_gap > 0:
                time_gaps.append(time_gap)

                # Check for large gaps (> 10 minutes = 600 seconds)
                if time_gap > 600:
                    metrics.data_gaps_large += 1

                # Distance in km
                distance = abs(curr.chainage - prev.chainage)
                distances.append(distance)

                # Speed in km/h
                if time_gap > 0:
                    speed = (distance / time_gap) * 3600  # Convert to km/h
                    speeds.append(speed)

                    # Check for speed spikes (> 200 km/h)
                    if speed > 200:
                        metrics.speed_spikes += 1

        # Calculate statistics
        if speeds:
            metrics.avg_speed_kmh = sum(speeds) / len(speeds)
            metrics.max_speed_kmh = max(speeds)
            metrics.min_speed_kmh = min(speeds) if min(speeds) > 0 else 0

        if time_gaps:
            metrics.time_gaps_count = len([g for g in time_gaps if g > 60])  # Gaps > 1 minute
            metrics.max_time_gap_seconds = max(time_gaps)
            metrics.avg_time_gap_seconds = sum(time_gaps) / len(time_gaps)

        if distances:
            metrics.avg_distance_between_points = sum(distances) / len(distances)
            metrics.max_distance_between_points = max(distances)

    def _calculate_quality_score(self, metrics: GPSQualityMetrics) -> float:
        """Calculate overall GPS quality score (0-100)"""
        if metrics.total_points == 0:
            return 0.0

        # Base score from data validity
        validity_ratio = metrics.valid_points / metrics.total_points

        # Penalty factors
        penalties = 0.0

        # Chainage issues
        chainage_error_rate = (metrics.chainage_negative + metrics.chainage_too_large +
                              metrics.chainage_nan + metrics.chainage_infinite +
                              metrics.chainage_non_monotonic) / metrics.total_points
        penalties += chainage_error_rate * 30

        # Timestamp issues
        timestamp_error_rate = (metrics.timestamp_invalid +
                               metrics.timestamp_out_of_order) / metrics.total_points
        penalties += timestamp_error_rate * 20

        # Coordinate issues
        coord_error_rate = (metrics.coord_invalid +
                           metrics.coord_out_of_bounds) / metrics.total_points
        penalties += coord_error_rate * 20

        # Data quality issues
        duplicate_rate = (metrics.duplicate_timestamps + metrics.duplicate_coordinates) / metrics.total_points
        penalties += duplicate_rate * 15

        # Speed anomalies
        if metrics.valid_points > 0:
            speed_anomaly_rate = metrics.speed_spikes / metrics.valid_points
            penalties += min(speed_anomaly_rate * 10, 10)  # Cap at 10 points

        # Time gaps penalty
        if metrics.valid_points > 0:
            gap_penalty = min(metrics.time_gaps_count / metrics.valid_points * 20, 10)
            penalties += gap_penalty

        # Large data gaps penalty
        if metrics.valid_points > 0:
            large_gap_penalty = min(metrics.data_gaps_large / metrics.valid_points * 25, 15)
            penalties += large_gap_penalty

        # Skipped rows penalty (high penalty for data loss)
        if metrics.total_points + metrics.skipped_rows > 0:
            skip_rate = metrics.skipped_rows / (metrics.total_points + metrics.skipped_rows)
            penalties += skip_rate * 40  # High penalty for skipped data

        # Calculate final score
        base_score = validity_ratio * 100
        final_score = max(0, min(100, base_score - penalties))

        return round(final_score, 1)

    def _calculate_risk_level(self, metrics: GPSQualityMetrics) -> str:
        """Calculate risk level based on quality metrics"""
        # High risk factors
        high_risk_factors = [
            metrics.skipped_rows > metrics.total_points * 0.3,  # >30% data skipped
            metrics.quality_score < 50,  # Low quality score
            metrics.data_gaps_large > 5,  # Many large gaps
            metrics.chainage_non_monotonic > metrics.total_points * 0.1,  # >10% non-monotonic
            metrics.speed_spikes > metrics.valid_points * 0.05 if metrics.valid_points > 0 else False  # >5% speed spikes
        ]

        # Medium risk factors
        medium_risk_factors = [
            metrics.skipped_rows > metrics.total_points * 0.1,  # >10% data skipped
            metrics.quality_score < 80,  # Moderate quality score
            metrics.data_gaps_large > 1,  # Some large gaps
            metrics.duplicate_timestamps > 0 or metrics.duplicate_coordinates > 0,  # Duplicates present
        ]

        if any(high_risk_factors):
            return "Critical"
        elif any(medium_risk_factors):
            return "High"
        elif metrics.quality_score < 95:
            return "Medium"
        else:
            return "Low"

    def generate_report(self) -> str:
        """Generate a comprehensive quality report"""
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("GPS QUALITY ANALYSIS REPORT")
        report_lines.append("=" * 80)
        report_lines.append(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append(f"Base Path: {self.base_path}")
        report_lines.append("")

        if not self.results:
            report_lines.append("No data folders found to analyze.")
            return "\n".join(report_lines)

        # Summary statistics
        total_folders = len(self.results)
        avg_quality = sum(m.quality_score for m in self.results.values()) / total_folders
        best_quality = max((m.quality_score, name) for name, m in self.results.items())
        worst_quality = min((m.quality_score, name) for name, m in self.results.items())

        # Risk level distribution
        risk_counts = {"Low": 0, "Medium": 0, "High": 0, "Critical": 0}
        for metrics in self.results.values():
            risk_counts[metrics.risk_level] += 1

        report_lines.append("SUMMARY STATISTICS:")
        report_lines.append(f"  Total folders analyzed: {total_folders}")
        report_lines.append(f"  Average quality score: {avg_quality:.1f}")
        report_lines.append(f"  Best quality folder: {best_quality[1]} ({best_quality[0]})")
        report_lines.append(f"  Worst quality folder: {worst_quality[1]} ({worst_quality[0]})")
        report_lines.append(f"  Risk distribution: Low={risk_counts['Low']}, Medium={risk_counts['Medium']}, High={risk_counts['High']}, Critical={risk_counts['Critical']}")
        report_lines.append("")

        # Detailed folder analysis
        report_lines.append("DETAILED FOLDER ANALYSIS:")
        report_lines.append("-" * 80)

        for folder_name, metrics in sorted(self.results.items(),
                                         key=lambda x: x[1].quality_score):
            report_lines.append(f"Folder: {folder_name}")
            report_lines.append(f"  Quality Score: {metrics.quality_score}/100 (Risk: {metrics.risk_level})")

            # Data overview
            report_lines.append("  Data Overview:")
            report_lines.append(f"    Total GPS points: {metrics.total_points}")
            if metrics.total_points > 0:
                report_lines.append(f"    Valid points: {metrics.valid_points} ({metrics.valid_points/metrics.total_points*100:.1f}%)")
                report_lines.append(f"    Invalid points: {metrics.invalid_points} ({metrics.invalid_points/metrics.total_points*100:.1f}%)")
            else:
                report_lines.append("    Valid points: 0 (0.0%)")
                report_lines.append("    Invalid points: 0 (0.0%)")
            if metrics.skipped_rows > 0:
                total_rows = metrics.total_points + metrics.skipped_rows
                report_lines.append(f"    Skipped rows: {metrics.skipped_rows} ({metrics.skipped_rows/total_rows*100:.1f}% of total)")

            # Issues breakdown
            if metrics.invalid_points > 0 or metrics.skipped_rows > 0 or metrics.duplicate_timestamps > 0 or metrics.duplicate_coordinates > 0:
                report_lines.append("  Issues Found:")
                if metrics.skipped_rows > 0:
                    report_lines.append(f"    Parsing errors: {metrics.skipped_rows} rows skipped")
                if metrics.chainage_negative > 0:
                    report_lines.append(f"    Chainage negative: {metrics.chainage_negative}")
                if metrics.chainage_too_large > 0:
                    report_lines.append(f"    Chainage too large: {metrics.chainage_too_large}")
                if metrics.chainage_nan > 0:
                    report_lines.append(f"    Chainage NaN/Infinite: {metrics.chainage_nan}")
                if metrics.chainage_non_monotonic > 0:
                    report_lines.append(f"    Non-monotonic chainage: {metrics.chainage_non_monotonic}")
                if metrics.timestamp_invalid > 0:
                    report_lines.append(f"    Invalid timestamps: {metrics.timestamp_invalid}")
                if metrics.timestamp_out_of_order > 0:
                    report_lines.append(f"    Out-of-order timestamps: {metrics.timestamp_out_of_order}")
                if metrics.coord_invalid > 0:
                    report_lines.append(f"    Invalid coordinates: {metrics.coord_invalid}")
                if metrics.coord_out_of_bounds > 0:
                    report_lines.append(f"    Coordinates out of bounds: {metrics.coord_out_of_bounds}")
                if metrics.duplicate_timestamps > 0:
                    report_lines.append(f"    Duplicate timestamps: {metrics.duplicate_timestamps}")
                if metrics.duplicate_coordinates > 0:
                    report_lines.append(f"    Duplicate coordinates: {metrics.duplicate_coordinates}")

            # Movement analysis
            if metrics.valid_points > 1:
                report_lines.append("  Movement Analysis:")
                report_lines.append(f"    Average speed: {metrics.avg_speed_kmh:.1f} km/h")
                report_lines.append(f"    Max speed: {metrics.max_speed_kmh:.1f} km/h")
                report_lines.append(f"    Min speed: {metrics.min_speed_kmh:.1f} km/h")
                if metrics.speed_spikes > 0:
                    report_lines.append(f"    Speed spikes (>200 km/h): {metrics.speed_spikes}")

                report_lines.append("  Data Density:")
                report_lines.append(f"    Avg distance between points: {metrics.avg_distance_between_points:.1f} km")
                report_lines.append(f"    Max distance between points: {metrics.max_distance_between_points:.1f} km")

                if metrics.time_gaps_count > 0:
                    report_lines.append(f"    Time gaps (>1 min): {metrics.time_gaps_count}")
                    report_lines.append(f"    Max time gap: {metrics.max_time_gap_seconds:.1f} seconds")
                    report_lines.append(f"    Avg time gap: {metrics.avg_time_gap_seconds:.1f} seconds")

                if metrics.data_gaps_large > 0:
                    report_lines.append(f"    Large gaps (>10 min): {metrics.data_gaps_large}")
            report_lines.append("")

        # Comparative Analysis
        if total_folders > 1:
            report_lines.append("COMPARATIVE ANALYSIS:")
            report_lines.append("-" * 80)

            # Find folders with significant differences
            all_metrics = list(self.results.values())
            avg_skipped = sum(m.skipped_rows for m in all_metrics) / total_folders
            avg_quality = sum(m.quality_score for m in all_metrics) / total_folders

            # Identify problematic folders
            problematic_folders = []
            for name, metrics in self.results.items():
                issues = []
                if metrics.skipped_rows > avg_skipped * 2:  # Skip rate > 2x average
                    issues.append(f"high skip rate ({metrics.skipped_rows} vs avg {avg_skipped:.1f})")
                if metrics.quality_score < avg_quality - 20:  # Quality > 20 points below average
                    issues.append(f"low quality ({metrics.quality_score} vs avg {avg_quality:.1f})")
                if metrics.risk_level in ["High", "Critical"]:
                    issues.append(f"high risk ({metrics.risk_level})")
                if metrics.data_gaps_large > 2:
                    issues.append(f"many large gaps ({metrics.data_gaps_large})")

                if issues:
                    problematic_folders.append((name, issues))

            if problematic_folders:
                report_lines.append("Folders requiring attention:")
                for name, issues in problematic_folders:
                    report_lines.append(f"  • {name}: {', '.join(issues)}")
                report_lines.append("")

            # Data pattern comparison
            report_lines.append("Data pattern comparison:")
            max_points = max(m.total_points for m in all_metrics)
            min_points = min(m.total_points for m in all_metrics)
            report_lines.append(f"  GPS points range: {min_points} - {max_points}")

            if all_metrics[0].skipped_rows > 0 or any(m.skipped_rows > 0 for m in all_metrics):
                max_skipped = max(m.skipped_rows for m in all_metrics)
                min_skipped = min(m.skipped_rows for m in all_metrics)
                report_lines.append(f"  Skipped rows range: {min_skipped} - {max_skipped}")

                # Highlight folders with high skip rates
                high_skip_folders = [(name, m) for name, m in self.results.items()
                                   if m.skipped_rows > avg_skipped * 1.5]
                if high_skip_folders:
                    report_lines.append("  Folders with high data loss:")
                    for name, m in high_skip_folders:
                        skip_pct = m.skipped_rows / (m.total_points + m.skipped_rows) * 100
                        report_lines.append(f"    - {name}: {skip_pct:.1f}% data skipped ({m.skipped_rows} rows)")
            report_lines.append("")

        # Recommendations
        report_lines.append("RECOMMENDATIONS:")
        report_lines.append("-" * 80)

        low_quality_folders = [(name, m) for name, m in self.results.items()
                              if m.quality_score < 50]

        if low_quality_folders:
            report_lines.append("Folders needing immediate attention:")
            for name, metrics in low_quality_folders:
                report_lines.append(f"  - {name}: Quality score {metrics.quality_score}")
                if metrics.skipped_rows > 0:
                    report_lines.append("    → High data loss during parsing - check file format")
                if metrics.chainage_non_monotonic > 0:
                    report_lines.append("    → Chainage data corrupted - may need manual correction")
                if metrics.timestamp_out_of_order > 0:
                    report_lines.append("    → Timestamp ordering issues - check data collection")
                if metrics.data_gaps_large > 0:
                    report_lines.append("    → Large time gaps - verify continuous data collection")
                if metrics.duplicate_timestamps > 0 or metrics.duplicate_coordinates > 0:
                    report_lines.append("    → Duplicate data points - check for data redundancy")
            report_lines.append("")

        report_lines.append("General recommendations:")
        report_lines.append("  • GPS data should have chainage values between 0-10,000 km")
        report_lines.append("  • Timestamps should be in chronological order")
        report_lines.append("  • Speed should be realistic (< 200 km/h for most vehicles)")
        report_lines.append("  • Time gaps between points should be reasonable (< 5 minutes)")
        report_lines.append("  • Consider implementing GPS data validation before processing")
        report_lines.append("  • Monitor for folders with high skip rates - may indicate format issues")
        report_lines.append("  • Large data gaps may cause rendering or analysis problems")

        return "\n".join(report_lines)

def main():
    """Main function"""
    import sys

    # Check command line arguments
    folder_paths = []
    if len(sys.argv) > 1:
        folder_paths = sys.argv[1:]

    if not folder_paths:
        # Default to the err folder
        script_dir = Path(__file__).parent
        base_path = script_dir / "testdata" / "err"
        analyzer = GPSQualityAnalyzer(base_path)
        results = analyzer.analyze_all_folders()
    else:
        # Analyze specific folders
        analyzer = GPSQualityAnalyzer(None)  # No base path needed
        for folder_path in folder_paths:
            folder = Path(folder_path)
            if folder.exists() and folder.is_dir():
                logger.info(f"Analyzing folder: {folder.name}")
                try:
                    metrics = analyzer.analyze_folder(folder)
                    analyzer.results[folder.name] = metrics
                except Exception as e:
                    logger.error(f"Error analyzing folder {folder.name}: {e}")
                    continue
            else:
                logger.error(f"Folder does not exist: {folder_path}")
        results = analyzer.results

    if not results:
        print("No folders found to analyze.")
        return

    # Generate and display report
    report = analyzer.generate_report()
    print(report)

    # Save report to file
    report_file = Path(__file__).parent / "gps_quality_report.txt"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"\nReport saved to: {report_file}")

if __name__ == "__main__":
    main()