import java.util.Scanner;

public class StudentGradingSystem {
   public static void main(String[] args) {
      Scanner scanner = new Scanner(System.in);
      
      int totalStudents = 5;
      int passedCount = 0;
      int failedCount = 0;
      double highestAverage = 0;
      double lowestAverage = 100;
      double totalClassAverage = 0;
      
      System.out.println("=== Student Registration: 5 Students ===");
      
      for (int i = 1; i <= totalStudents;i++) {
      System.out.println("\n--- Student "+i+"---");
      
      System.out.print("Enter student name: ");
      String name = scanner.nextLine();
      
      System.out.print("Enter midterm grade: ");
      double midterm = scanner.nextDouble();
      
      System.out.print("Enter final grade: ");
      double finalGrade = scanner.nextDouble();
      scanner.nextLine();
      
      double average = (midterm + finalGrade)/2.0;
      
      String remark;
      if (average >= 90 && average <= 100) {
      remark = "Excellent";
      } else if (average >= 85 && average <= 89) {
      remark = "Very Good";
      } else if (average >= 80 && average <= 84) {
      remark = "Good";
      } else if (average >= 75 && average <= 79) {
      remark = "Passed";
      } else {
      remark = "Failed";
      }
      
      System.out.println("\nResult for" + name);
      System.out.println("Average Grade: %.2f\n" + average);
      System.out.println("Remark: " + remark);
      
      totalClassAverage += average;
      
      if (average >= 75) {
      passedCount++;
      } else {
      failedCount++;
      }
      
      if (average > highestAverage) {
      highestAverage = average;
      }
      
      if (average < lowestAverage) {
      lowestAverage = average;
      }
      }
      
      double classAverage = totalClassAverage/totalStudents;
      
      System.out.println("\n====CLASS SUMMARY====");
      System.out.println("Total Students Passed: " + passedCount);
      System.out.println("Total Students Failed:" + failedCount);
      System.out.printf("Highest Average: %.2f\n", highestAverage);
      System.out.printf("Lowest Average: %.2f\n", lowestAverage);
      System.out.printf("Class Average: %.2f\n", classAverage);
      System.out.println("============");
      
      scanner.close();
   }
}