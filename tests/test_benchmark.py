import os
import sys
import time
import asyncio
import statistics
from datetime import datetime
import json
import traceback
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Any, Optional

# Import functions from test_playwright
from tests.test_playwright import (
    integration_test,
    create_test_user,
    generate_and_save_files,
    app,
    setup_gemini
)

@dataclass
class StepMetrics:
    name: str
    start_time: float = 0
    end_time: float = 0
    success: bool = False
    error_message: Optional[str] = None

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['duration'] = self.duration
        return result

@dataclass
class TestRunMetrics:
    run_id: int
    browser_type: str
    start_time: float
    steps: List[StepMetrics] = field(default_factory=list)
    end_time: float = 0
    success: bool = False
    
    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time
    
    def add_step(self, name: str) -> StepMetrics:
        step = StepMetrics(name=name, start_time=time.time())
        self.steps.append(step)
        return step
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        result['total_duration'] = self.total_duration
        result['timestamp'] = datetime.fromtimestamp(self.start_time).isoformat()
        result['steps'] = [step.to_dict() for step in self.steps]
        return result

@dataclass
class BenchmarkResults:
    test_name: str = "PlaywrightBenchmark"
    start_time: float = field(default_factory=time.time)
    runs: List[TestRunMetrics] = field(default_factory=list)
    end_time: float = 0
    
    def add_run(self, run_id: int, browser_type: str) -> TestRunMetrics:
        run = TestRunMetrics(run_id=run_id, browser_type=browser_type, start_time=time.time())
        self.runs.append(run)
        return run
    
    @property
    def total_duration(self) -> float:
        return self.end_time - self.start_time
    
    @property
    def success_rate(self) -> float:
        if not self.runs:
            return 0
        return sum(1 for run in self.runs if run.success) / len(self.runs) * 100
    
    def get_step_stats(self, step_name: str) -> Dict[str, Any]:
        step_durations = [step.duration for run in self.runs for step in run.steps 
                         if step.name == step_name and step.success]
        
        if not step_durations:
            return {
                "min": 0,
                "max": 0,
                "avg": 0,
                "median": 0,
                "success_rate": 0
            }
        
        total_steps = sum(1 for run in self.runs for step in run.steps if step.name == step_name)
        successful_steps = len(step_durations)
        
        return {
            "min": min(step_durations) if step_durations else 0,
            "max": max(step_durations) if step_durations else 0,
            "avg": statistics.mean(step_durations) if step_durations else 0,
            "median": statistics.median(step_durations) if step_durations else 0,
            "success_rate": (successful_steps / total_steps * 100) if total_steps else 0
        }
    
    def get_browser_stats(self) -> Dict[str, Dict[str, Any]]:
        browsers = set(run.browser_type for run in self.runs)
        result = {}
        
        for browser in browsers:
            browser_runs = [run for run in self.runs if run.browser_type == browser]
            successful_runs = [run for run in browser_runs if run.success]
            
            durations = [run.total_duration for run in successful_runs]
            result[browser] = {
                "runs": len(browser_runs),
                "successful": len(successful_runs),
                "success_rate": len(successful_runs) / len(browser_runs) * 100 if browser_runs else 0,
                "avg_duration": statistics.mean(durations) if durations else 0,
                "min_duration": min(durations) if durations else 0,
                "max_duration": max(durations) if durations else 0
            }
        
        return result
    
    def generate_report(self) -> str:
        self.end_time = time.time()
        
        step_names = set()
        for run in self.runs:
            for step in run.steps:
                step_names.add(step.name)
        
        step_stats = {name: self.get_step_stats(name) for name in step_names}
        browser_stats = self.get_browser_stats()
        
        report = [
            "═════════════════════════════════════════",
            f"  PLAYWRIGHT BENCHMARK RESULTS: {self.test_name}",
            "═════════════════════════════════════════",
            f"Date: {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}",
            f"Total Duration: {self.total_duration:.2f}s ({self.total_duration/60:.1f}m)",
            f"Runs: {len(self.runs)}",
            f"Success Rate: {self.success_rate:.1f}%",
            "",
            "───── BROWSER PERFORMANCE ─────"
        ]
        
        for browser, stats in browser_stats.items():
            report.append(f"Browser: {browser}")
            report.append(f"  Runs: {stats['runs']}")
            report.append(f"  Success Rate: {stats['success_rate']:.1f}%")
            report.append(f"  Avg Duration: {stats['avg_duration']:.2f}s")
            report.append(f"  Min/Max: {stats['min_duration']:.2f}s / {stats['max_duration']:.2f}s")
            report.append("")
        
        report.append("───── STEP PERFORMANCE ─────")
        for name, stats in step_stats.items():
            report.append(f"Step: {name}")
            report.append(f"  Success Rate: {stats['success_rate']:.1f}%")
            report.append(f"  Avg Duration: {stats['avg']*1000:.0f}ms")
            report.append(f"  Min/Max: {stats['min']*1000:.0f}ms / {stats['max']*1000:.0f}ms")
            report.append("")
        
        report.append("───── DETAILED RUN INFORMATION ─────")
        for run in self.runs:
            run_status = "✓" if run.success else "✗"
            report.append(f"Run {run.run_id} ({run.browser_type}): {run_status} - {run.total_duration:.2f}s")
            for step in run.steps:
                step_status = "✓" if step.success else "✗"
                report.append(f"  • {step.name}: {step_status} - {step.duration*1000:.0f}ms")
                if not step.success and step.error_message:
                    report.append(f"    Error: {step.error_message}")
            report.append("")
        
        report.append("═════════════════════════════════════════")
        return "\n".join(report)

    def save_report(self, filename: str = "benchmark_results.txt") -> None:
        report = self.generate_report()
        with open(filename, "w") as f:
            f.write(report)
        print(f"Report saved to {os.path.abspath(filename)}")
        
    def save_json(self, filename: str = "benchmark_results.json") -> None:
        data = {
            "test_name": self.test_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat(),
            "total_duration": self.total_duration,
            "runs": [run.to_dict() for run in self.runs],
            "success_rate": self.success_rate,
            "step_stats": {name: self.get_step_stats(name) 
                          for name in set(step.name for run in self.runs for step in run.steps)},
            "browser_stats": self.get_browser_stats()
        }
        with open(filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"JSON data saved to {os.path.abspath(filename)}")


# Modified benchmark version of the integration test
async def benchmark_integration_test(run_metrics: TestRunMetrics, browser_types: List[str] = None) -> None:
    """Run the integration test with performance measurement"""
    if browser_types is None:
        browser_types = ['webkit', 'firefox']  # Default browsers to test
        
    test_url = "https://jobs.ashbyhq.com/replo/ec206174-ccc2-42fa-b295-8201421f21b0/application"
    
    for browser_type_name in browser_types:
        run_metrics.browser_type = browser_type_name
        print(f"\nStarting benchmark with {browser_type_name} browser...")
        
        # Step 1: Initialize browser
        step = run_metrics.add_step("Initialize Browser")
        try:
            from playwright.async_api import async_playwright
            playwright = await async_playwright().start()
            browser_type = getattr(playwright, browser_type_name)
            step.success = True
        except Exception as e:
            step.error_message = str(e)
            print(f"Error initializing browser: {e}")
            return
        finally:
            step.end_time = time.time()
            
        # Step 2: Launch browser
        step = run_metrics.add_step("Launch Browser")
        try:
            browser = await browser_type.launch(
                headless=True,
                slow_mo=50,
                args=[] if browser_type_name != 'chromium' else [
                    "--no-sandbox",
                    "--disable-gpu",
                    "--disable-dev-shm-usage"
                ]
            )
            context = await browser.new_context(viewport={'width': 1280, 'height': 720})
            page = await context.new_page()
            step.success = True
        except Exception as e:
            step.error_message = str(e)
            print(f"Error launching browser: {e}")
            await playwright.stop()
            return
        finally:
            step.end_time = time.time()
        
        try:
            # Step 3: Navigate to test URL
            step = run_metrics.add_step("Navigate to Website")
            try:
                await page.goto(test_url, timeout=60000)
                await page.wait_for_load_state('networkidle', timeout=10000)
                page_title = await page.title()
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error navigating to URL: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 4: Create test user
            step = run_metrics.add_step("Create Test User")
            try:
                with app.app_context():
                    user_data = create_test_user(use_real_user=False)
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error creating test user: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 5: Generate cover letter and resume
            step = run_metrics.add_step("Generate Documents")
            try:
                with app.app_context():
                    cover_letter_path, resume_path, user_data = generate_and_save_files(user_data)
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error generating documents: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 6: Find form elements
            step = run_metrics.add_step("Find Form Elements")
            try:
                form_elements = await page.query_selector_all('form')
                input_elements = await page.query_selector_all('input')
                file_inputs = await page.query_selector_all('input[type="file"]')
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error finding form elements: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 7: Upload resume if file inputs exist
            step = run_metrics.add_step("Upload Resume")
            try:
                if file_inputs:
                    for file_input in file_inputs:
                        try:
                            await page.evaluate("""input => {
                                if (input && input.parentElement) {
                                    input.style.opacity = '1';
                                    input.style.display = 'block';
                                    input.style.visibility = 'visible';
                                }
                            }""", file_input)
                            await file_input.set_input_files(resume_path)
                            break
                        except Exception:
                            continue
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error uploading resume: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 8: Fill form fields
            step = run_metrics.add_step("Fill Form Fields")
            try:
                name_selectors = ['input[name="name"]', 'input[placeholder*="name" i]', 
                                 'input[id*="name" i]', 'input[type="text"]']
                email_selectors = ['input[name="email"]', 'input[placeholder*="email" i]', 
                                  'input[id*="email" i]', 'input[type="email"]']
                
                for selector in name_selectors:
                    try:
                        name_input = await page.query_selector(selector)
                        if name_input:
                            await name_input.fill(user_data["name"])
                            break
                    except Exception:
                        continue
                
                for selector in email_selectors:
                    try:
                        email_input = await page.query_selector(selector)
                        if email_input:
                            await email_input.fill(user_data["email"])
                            break
                    except Exception:
                        continue
                
                textareas = await page.query_selector_all('textarea')
                if textareas:
                    skills = user_data["skills"]
                    response = f"I am {user_data['name']}, with expertise in {', '.join(skills[:3])}."
                    
                    for textarea in textareas:
                        try:
                            await textarea.fill(response)
                        except Exception:
                            continue
                
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error filling form fields: {e}")
            finally:
                step.end_time = time.time()
            
            # Step 9: Find submit button
            step = run_metrics.add_step("Find Submit Button")
            try:
                button_selectors = [
                    'button[type="submit"]',
                    'input[type="submit"]',
                    'button:has-text("Submit")',
                    'button:has-text("Apply")',
                ]
                
                for selector in button_selectors:
                    try:
                        button = await page.query_selector(selector)
                        if button and await button.is_visible():
                            break
                    except Exception:
                        continue
                
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error finding submit button: {e}")
            finally:
                step.end_time = time.time()
            
            # Mark the run as successful if we got this far
            run_metrics.success = True
            
        except Exception as e:
            print(f"Unexpected error during test: {e}")
            traceback.print_exc()
        finally:
            # Step 10: Cleanup
            step = run_metrics.add_step("Cleanup")
            try:
                await browser.close()
                await playwright.stop()
                # Clean up generated files
                if 'cover_letter_path' in locals() and os.path.exists(cover_letter_path):
                    os.remove(cover_letter_path)
                if 'resume_path' in locals() and os.path.exists(resume_path):
                    os.remove(resume_path)
                step.success = True
            except Exception as e:
                step.error_message = str(e)
                print(f"Error during cleanup: {e}")
            finally:
                step.end_time = time.time()
        
        # Record the end time for the run
        run_metrics.end_time = time.time()
        print(f"Run completed in {run_metrics.total_duration:.2f}s with status: {'Success' if run_metrics.success else 'Failed'}")
        
        # Only test one browser per run for benchmark clarity
        break


async def run_benchmark(num_runs: int = 3) -> None:
    """Run the benchmark for a specified number of runs"""
    benchmark_results = BenchmarkResults()
    browser_types = ['webkit', 'firefox']  # 'chromium' removed due to instability
    
    # Alternate browsers for each run to distribute tests
    for i in range(num_runs):
        # Choose browser for this run
        browser_idx = i % len(browser_types)
        browser_type = browser_types[browser_idx]
        
        print(f"\n[Run {i+1}/{num_runs}] Starting benchmark run with {browser_type}...")
        run = benchmark_results.add_run(i+1, browser_type)
        
        try:
            await benchmark_integration_test(run, [browser_type])
        except Exception as e:
            print(f"Error in benchmark run {i+1}: {e}")
            traceback.print_exc()
        
    # Record end time and generate report
    benchmark_results.end_time = time.time()
    
    # Display the report
    print("\n" + benchmark_results.generate_report())
    
    # Save report and raw data
    benchmark_results.save_report()
    benchmark_results.save_json()


if __name__ == "__main__":
    num_runs = 3
    if len(sys.argv) > 1:
        try:
            num_runs = int(sys.argv[1])
        except ValueError:
            print(f"Invalid argument: {sys.argv[1]}. Using default: 3 runs")
    
    print(f"Starting playwright benchmark with {num_runs} runs...")
    asyncio.run(run_benchmark(num_runs))