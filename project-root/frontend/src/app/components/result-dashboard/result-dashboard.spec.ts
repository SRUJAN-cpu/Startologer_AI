import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ResultDashboard } from './result-dashboard';

describe('ResultDashboard', () => {
  let component: ResultDashboard;
  let fixture: ComponentFixture<ResultDashboard>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResultDashboard]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ResultDashboard);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
