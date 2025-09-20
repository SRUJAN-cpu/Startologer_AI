import { ComponentFixture, TestBed } from '@angular/core/testing';

import { TrailMode } from './trail-mode';

describe('TrailMode', () => {
  let component: TrailMode;
  let fixture: ComponentFixture<TrailMode>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [TrailMode]
    })
    .compileComponents();

    fixture = TestBed.createComponent(TrailMode);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
