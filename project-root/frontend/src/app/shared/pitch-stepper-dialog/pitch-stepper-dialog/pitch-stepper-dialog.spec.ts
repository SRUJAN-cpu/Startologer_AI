import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PitchStepperDialog } from './pitch-stepper-dialog';

describe('PitchStepperDialog', () => {
  let component: PitchStepperDialog;
  let fixture: ComponentFixture<PitchStepperDialog>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PitchStepperDialog]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PitchStepperDialog);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
